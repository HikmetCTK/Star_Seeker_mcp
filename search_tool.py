import json
import os
import re
import pickle
import numpy as np

# --- Import & Setup Google GenAI ---
try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

# --- Import & Setup SentenceTransformers (Fallback) ---
try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers import util
    HAS_LOCAL_VECTORS = True
except ImportError:
    HAS_LOCAL_VECTORS = False

class StarSearcher:
    def __init__(self, json_path):
        self.json_path = json_path
        self.cache_path = json_path.replace(".json", "_embeddings.pkl")
        
        self.repos = []
        self.descriptions = []
        self.search_texts = []
        
        self.embedding_source = "keyword" # default
        self.embeddings = None
        self.google_client = None
        self.local_model = None

        # 1. Initialize Google Client
        api_key = os.getenv("GEMINI_API_KEY")
        if HAS_GOOGLE and api_key:
            try:
                self.google_client = genai.Client(api_key=api_key)
                self.embedding_source = "google"
            except Exception as e:
                print(f"Warning: Failed to init Google Client: {e}")
        
        # 2. Initialize Local Model (as backup)
        if self.embedding_source == "keyword" and HAS_LOCAL_VECTORS:
            self.embedding_source = "local"
            print("Loading local AI model (fallback)...")
            self.local_model = SentenceTransformer('all-MiniLM-L6-v2')

        self.load_data()

    def load_data(self):
        if not os.path.exists(self.json_path):
            print(f"Error: {self.json_path} not found. Fetch data first.")
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            self.repos = json.load(f)
        
        self.descriptions = []
        self.search_texts = []
        
        for repo in self.repos:
            desc = repo.get("description") or ""
            topics = " ".join(repo.get("topics", []))
            full_text = f"{repo['full_name']} {desc} {topics}"
            
            self.descriptions.append(full_text)
            self.search_texts.append(full_text.lower())

        # Build or Load Embeddings
        if self.embedding_source != "keyword":
            self._load_or_build_embeddings()

    def _load_or_build_embeddings(self):
        # Try loading from cache
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "rb") as f:
                data = pickle.load(f)
                # Verify cache matches current data source and count
                if data.get("source") == self.embedding_source and len(data.get("vectors")) == len(self.descriptions):
                    print(f"Loaded {self.embedding_source} embeddings from cache.")
                    self.embeddings = data["vectors"]
                    return
                else:
                    print("Cache outdated or mismatch. Rebuilding...")

        print(f"Building {self.embedding_source} index (this happens once)...")
        
        if self.embedding_source == "google":
            self.embeddings = self._build_google_embeddings()
        elif self.embedding_source == "local":
            self.embeddings = self.local_model.encode(self.descriptions, convert_to_tensor=True)
            self.embeddings = self.embeddings.cpu().numpy() # Store as numpy for consistency
        
        # Save to cache
        with open(self.cache_path, "wb") as f:
            pickle.dump({
                "source": self.embedding_source,
                "vectors": self.embeddings
            }, f)
        print("Index saved.")

    def _build_google_embeddings(self):
        vectors = []
        batch_size = 100 
        total = len(self.descriptions)
        
        print(f"Embedding {total} items with Google Gemini (True Batching)...")
        
        for i in range(0, total, batch_size):
            batch = self.descriptions[i:i + batch_size]
            try:
                # True Batching: Send the whole list at once
                result = self.google_client.models.embed_content(
                    model="text-embedding-004",
                    contents=batch
                )
                for embedding in result.embeddings:
                    vectors.append(embedding.values)
                print(f"  Processed {min(i + batch_size, total)}/{total}")
            except Exception as e:
                print(f"Google Embedding Error: {e}")
                print("Falling back to keyword search for this session.")
                self.embedding_source = "keyword"
                return None
                
        return np.array(vectors)

    def search(self, query):
        if " and " in query.lower() or " & " in query:
            split_queries = re.split(r'\s+(?:and|&)\s+', query.lower())
            aggregated_results = {}
            for sub_query in split_queries:
                sub_results = self._execute_search(sub_query, limit=5)
                aggregated_results[sub_query] = sub_results
            return aggregated_results
        else:
            return {query: self._execute_search(query, limit=5)}

    def _execute_search(self, query, limit=5):
        if self.embedding_source == "google" and self.embeddings is not None:
            return self.google_vector_search(query, limit)
        elif self.embedding_source == "local" and self.embeddings is not None:
            # Re-wrap in tensor for util.semantic_search if using sentence-transformers util
            # Or just use numpy cosine sim
            return self.local_vector_search(query, limit)
        else:
            return self.keyword_search(query, limit)

    def google_vector_search(self, query, limit=5):
        try:
            result = self.google_client.models.embed_content(
                model="text-embedding-004",
                contents=query
            )
            query_vec = np.array(result.embeddings[0].values)
            
            # Compute Cosine Similarity manually using numpy
            # (A . B) / (|A| * |B|)
            # Assuming vectors might not be normalized
            scores = []
            norm_q = np.linalg.norm(query_vec)
            
            for idx, doc_vec in enumerate(self.embeddings):
                norm_d = np.linalg.norm(doc_vec)
                if norm_d == 0 or norm_q == 0:
                    score = 0
                else:
                    score = np.dot(query_vec, doc_vec) / (norm_q * norm_d)
                scores.append((score, idx))
            
            scores.sort(key=lambda x: x[0], reverse=True)
            return [self.repos[idx] for score, idx in scores[:limit]]
            
        except Exception as e:
            print(f"Search Error: {e}")
            return self.keyword_search(query, limit)

    def local_vector_search(self, query, limit=5):
        # Fallback to util if available
        if HAS_LOCAL_VECTORS:
            query_embedding = self.local_model.encode(query, convert_to_tensor=True)
            # Ensure embeddings are tensor
            doc_embeddings = self.local_model.encode(self.descriptions, convert_to_tensor=True) 
            hits = util.semantic_search(query_embedding, doc_embeddings, top_k=limit)
             
            results = []
            for hit in hits[0]:
                idx = hit['corpus_id']
                results.append(self.repos[idx])
            return results
        return self.keyword_search(query, limit)

    def keyword_search(self, query, limit=5):
        query_terms = query.lower().split()
        scores = []
        for idx, text in enumerate(self.search_texts):
            score = 0
            for term in query_terms:
                if term in text:
                    score += 1
            if score > 0:
                scores.append((score, self.repos[idx]))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scores[:limit]]

if __name__ == "__main__":
    user_file = input("Enter username for test: ").strip()
    path = f"{user_file}_stars.json"
    if os.path.exists(path):
        s = StarSearcher(path)
        print(f"Using Search Engine: {s.embedding_source.upper()}")
        while True:
            q = input("\nQuery: ")
            if q == 'q': break
            res = s.search(q)
            print(res)
