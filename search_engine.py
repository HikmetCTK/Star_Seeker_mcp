"""
Core search engine for GitHub stars.
Implements Hybrid Search (BM25 + Google Gemini Embeddings) with Reciprocal Rank Fusion (RRF).
"""

import os
import json
import pickle
import numpy as np
from rank_bm25 import BM25Okapi
from config import get_data_dir, logger

DATA_DIR = get_data_dir()

# Optional dependency: Google GenAI for embeddings
try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

class StarSearcher:
    """
    Searcher class to index and query a user's starred repositories.
    """
    def __init__(self, username):
        self.username = username
        self.json_path = str(DATA_DIR / f"{username}_stars.json")
        self.cache_path = str(DATA_DIR / f"{username}_stars_embeddings.pkl")
        
        self.repos = []
        self.descriptions = []
        self.embeddings = None
        self.embedding_source = "keyword" # Default to keyword if AI fails
        self.google_client = None
        self.bm25 = None

        # 1. Initialize Google Client if API Key is present
        api_key = os.getenv("GEMINI_API_KEY")
        if HAS_GOOGLE and api_key:
            try:
                self.google_client = genai.Client(api_key=api_key)
                self.embedding_source = "google"
            except Exception as e:
                logger.error(f"Failed to init Google Client: {e}")
        
        self.load_data()

    def load_data(self):
        """Loads repository metadata and initializes search indices."""
        if not os.path.exists(self.json_path):
            logger.warning(f"No JSON data found at {self.json_path}")
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            self.repos = json.load(f)
        
        # Prepare text for indexing (Name + Description + Topics)
        self.descriptions = []
        for repo in self.repos:
            desc = repo.get("description") or ""
            topics = " ".join(repo.get("topics", []))
            full_text = f"{repo['full_name']} {desc} {topics}"
            self.descriptions.append(full_text)
        
        # Build BM25 index (keyword-based)
        if self.descriptions:
            tokenized_corpus = [doc.lower().split() for doc in self.descriptions]
            self.bm25 = BM25Okapi(tokenized_corpus)

        # Build/Load Vector index (semantic-based) if Gemini is enabled
        if self.embedding_source == "google" and self.descriptions:
            self._load_or_build_embeddings()

    def _load_or_build_embeddings(self):
        """Attempts to load embeddings from cache, otherwise builds them."""
        # Try loading from local pickle cache to save API quota
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "rb") as f:
                    data = pickle.load(f)
                    # Verify cache validity (source matches and count matches)
                    if data.get("source") == "google" and len(data.get("vectors")) == len(self.descriptions):
                        self.embeddings = data["vectors"]
                        return
            except Exception as e:
                logger.debug(f"Cache load failed: {e}")

        # Cache miss or invalid: Build new embeddings
        self.embeddings = self._build_google_embeddings()
        
        if self.embeddings is not None:
            # Save to cache
            with open(self.cache_path, "wb") as f:
                pickle.dump({
                    "source": "google",
                    "vectors": self.embeddings
                }, f)

    def _build_google_embeddings(self):
        """Calls Google Gemini API to generate embeddings for all repo descriptions."""
        vectors = []
        batch_size = 100
        total = len(self.descriptions)
        
        logger.info(f"Generating semantic embeddings for {total} repos for user {self.username}...")
        
        for i in range(0, total, batch_size):
            batch = self.descriptions[i:i + batch_size]
            try:
                result = self.google_client.models.embed_content(
                    model="text-embedding-004",
                    contents=batch
                )
                for embedding in result.embeddings:
                    vectors.append(embedding.values)
                logger.info(f"Processed {min(i + batch_size, total)}/{total}")
            except Exception as e:
                logger.error(f"Google Embedding Error at batch {i}: {e}")
                return None
                
        return np.array(vectors)

    def search(self, query, limit=5):
        """
        Main gateway for searching. 
        Will use Hybrid, BM25, or Simple Keyword search based on availability.
        """
        if self.embeddings is not None and self.bm25:
            return self.hybrid_search(query, limit)
        
        if self.bm25:
            return self.bm25_search(query, limit)
        
        return self.simple_keyword_search(query, limit)

    def hybrid_search(self, query, limit=10):
        """
        Performs Hybrid Search using Reciprocal Rank Fusion (RRF).
        Combines Semantic (Vector) and Keyword (BM25) results.
        """
        # 1. Get Vector Scores (Semantic Similarity)
        try:
            result = self.google_client.models.embed_content(
                model="text-embedding-004",
                contents=query
            )
            query_vec = np.array(result.embeddings[0].values)
            
            vector_scores = []
            norm_q = np.linalg.norm(query_vec)
            for idx, doc_vec in enumerate(self.embeddings):
                norm_d = np.linalg.norm(doc_vec)
                score = np.dot(query_vec, doc_vec) / (norm_q * norm_d) if norm_d > 0 and norm_q > 0 else 0
                vector_scores.append((score, idx))
            
            # Rank indices by vector score
            vector_scores.sort(key=lambda x: x[0], reverse=True)
            vector_ranks = {idx: rank for rank, (score, idx) in enumerate(vector_scores)}
        except Exception as e:
            logger.error(f"Hybrid: Vector part failed: {e}")
            return self.bm25_search(query, limit)

        # 2. Get BM25 Scores (Keyword Match)
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        indexed_bm25 = list(enumerate(bm25_scores))
        indexed_bm25.sort(key=lambda x: x[1], reverse=True)
        bm25_ranks = {idx: rank for rank, (score, idx) in enumerate(indexed_bm25)}

        # 3. Combine using Reciprocal Rank Fusion (RRF)
        # Score = 1/(k + rank_vector) + 1/(k + rank_bm25)
        k = 60 # Constant to tune the influence of high vs low ranks
        fused_scores = []
        for i in range(len(self.repos)):
            # Only consider items that have at least some match in either algorithm
            if bm25_scores[i] > 0 or i in vector_ranks:
                v_rank = vector_ranks.get(i, len(self.repos))
                b_rank = bm25_ranks.get(i, len(self.repos))
                
                rrf_score = 1.0 / (k + v_rank) + 1.0 / (k + b_rank)
                fused_scores.append((rrf_score, i))
        
        fused_scores.sort(key=lambda x: x[0], reverse=True)
        return [self.repos[idx] for score, idx in fused_scores[:limit]]

    def bm25_search(self, query, limit=5):
        """Standard BM25 keyword search."""
        if not self.bm25:
            return self.simple_keyword_search(query, limit)
        tokenized_query = query.lower().split()
        return self.bm25.get_top_n(tokenized_query, self.repos, n=limit)

    def simple_keyword_search(self, query, limit=5):
        """Fallback keyword search using basic string matching."""
        query_terms = query.lower().split()
        results = []
        for repo in self.repos:
            text = f"{repo['full_name']} {repo.get('description') or ''} {' '.join(repo.get('topics', []))}".lower()
            score = sum(1 for term in query_terms if term in text)
            if score > 0:
                results.append((score, repo))
        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:limit]]

def test_search():
    """Simple test function to verify search functionality when run directly."""
    json_files = list(DATA_DIR.glob("*_stars.json"))
    if not json_files:
        print(f"No star data found in {DATA_DIR}. Please run fetch_stars first.")
        return

    username = json_files[0].stem.replace("_stars", "")
    query = "python machine learning"
    
    print(f"--- Testing StarSearcher for user: {username} ---")
    print(f"Query: {query}")
    
    try:
        searcher = StarSearcher(username)
        results = searcher.search(query, limit=5)
        
        print(f"Found {len(results)} results:")
        for i, r in enumerate(results, 1):
            desc = r.get('description') or 'No description'
            print(f"{i}. {r['full_name']} | {r['url']}")
            print(f"   Description: {desc[:100]}...")
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search()
