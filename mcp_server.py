from fastmcp import FastMCP
import os
import json
import requests
from dotenv import load_dotenv
import re
import pickle
import numpy as np

# Load local environment
load_dotenv()

# --- RE-IMPLEMENTED LOGIC TO AVOID IMPORTS ---

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

MCP_SYSTEM_PROMPT = """
You are a GitHub Star Recommender. Your goal is to help users find interesting repositories from their own starred list.
CRITICAL: Always ask the user for their GitHub username before calling any tool. 
Do NOT guess, predict, or assume the username.
"""

def raw_fetch_user_stars(username, token=None):
    """Internal implementation of star fetching."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    all_repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"https://api.github.com/users/{username}/starred?page={page}&per_page={per_page}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                break
            data = response.json()
            if not data:
                break
            for repo in data:
                if repo.get("stargazers_count", 0) < 10: # Filter out repositories with less than 10 stars
                    continue
                all_repos.append({
                    "full_name": repo.get("full_name"),
                    "language": repo.get("language"),
                    "description": repo.get("description"),
                    "url": repo.get("html_url"),
                    "stars": repo.get("stargazers_count"),
                    "topics": repo.get("topics", [])
                })
            if len(data) < per_page:
                break
            page += 1
            # Safety break to avoid infinite loops in test
            if page > 10: break
        except:
            break
            
    return all_repos

class StarSearcher:
    def __init__(self, username):
        self.username = username
        self.json_path = f"{username}_stars.json"
        self.cache_path = f"{username}_stars_embeddings.pkl"
        
        self.repos = []
        self.descriptions = []
        self.embeddings = None
        self.embedding_source = "keyword"
        self.google_client = None

        # 1. Initialize Google Client
        api_key = os.getenv("GEMINI_API_KEY")
        if HAS_GOOGLE and api_key:
            try:
                self.google_client = genai.Client(api_key=api_key)
                self.embedding_source = "google"
            except Exception as e:
                print(f"Warning: Failed to init Google Client: {e}")
        
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.json_path):
            return

        with open(self.json_path, "r", encoding="utf-8") as f:
            self.repos = json.load(f)
        
        self.descriptions = []
        for repo in self.repos:
            desc = repo.get("description") or ""
            topics = " ".join(repo.get("topics", []))
            full_text = f"{repo['full_name']} {desc} {topics}"
            self.descriptions.append(full_text)

        if self.embedding_source == "google" and self.descriptions:
            self._load_or_build_embeddings()

    def _load_or_build_embeddings(self):
        # Try loading from cache
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "rb") as f:
                    data = pickle.load(f)
                    if data.get("source") == "google" and len(data.get("vectors")) == len(self.descriptions):
                        self.embeddings = data["vectors"]
                        return
            except:
                pass

        # Build embeddings
        self.embeddings = self._build_google_embeddings()
        
        if self.embeddings is not None:
            with open(self.cache_path, "wb") as f:
                pickle.dump({
                    "source": "google",
                    "vectors": self.embeddings
                }, f)

    def _build_google_embeddings(self):
        vectors = []
        # Gemini supports up to 2048 items per call, but 100 is a safe, efficient balance
        batch_size = 100 
        total = len(self.descriptions)
        
        for i in range(0, total, batch_size):
            batch = self.descriptions[i:i + batch_size]
            try:
                # True Batching: One API call for the entire list
                result = self.google_client.models.embed_content(
                    model="text-embedding-004",
                    contents=batch
                )
                # Result contains a list of embeddings matching the batch order
                for embedding in result.embeddings:
                    vectors.append(embedding.values)
            except Exception as e:
                print(f"Google Embedding Error: {e}")
                self.embedding_source = "keyword"
                return None
                
        return np.array(vectors)

    def search(self, query, limit=5):
        if self.embedding_source == "google" and self.embeddings is not None:
            return self.google_vector_search(query, limit)
        return self.keyword_search(query, limit)

    def google_vector_search(self, query, limit=5):
        try:
            result = self.google_client.models.embed_content(
                model="text-embedding-004",
                contents=query
            )
            query_vec = np.array(result.embeddings[0].values)
            
            scores = []
            norm_q = np.linalg.norm(query_vec)
            
            for idx, doc_vec in enumerate(self.embeddings):
                norm_d = np.linalg.norm(doc_vec)
                score = np.dot(query_vec, doc_vec) / (norm_q * norm_d) if norm_d > 0 and norm_q > 0 else 0
                scores.append((score, idx))
            
            scores.sort(key=lambda x: x[0], reverse=True)
            return [self.repos[idx] for score, idx in scores[:limit]]
        except:
            return self.keyword_search(query, limit)

    def keyword_search(self, query, limit=5):
        query_terms = query.lower().split()
        results = []
        for repo in self.repos:
            text = f"{repo['full_name']} {repo.get('description') or ''} {' '.join(repo.get('topics', []))}".lower()
            score = sum(1 for term in query_terms if term in text)
            if score > 0:
                results.append((score, repo))
        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:limit]]

# Initialize FastMCP
mcp = FastMCP("GitHub Stars Recommender")

@mcp.tool(name="update_stars_for_user")
def fetch_stars_tool(username: str, token: str = None) -> str:
    """
    Fetch or update the database of starred repositories for a specific GitHub username.

    
    Args:
        username: The exact GitHub username provided by the user.
        token: Optional GitHub personal access token for higher rate limits.
    """
    api_token = token or os.getenv("GITHUB_TOKEN")
    try:
        stars = raw_fetch_user_stars(username, api_token)
        filename = f"{username}_stars.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(stars, f, indent=4)
        
        # Trigger embedding update if Gemini is available
        searcher = StarSearcher(username)
        status = " (Embedded with Gemini)" if searcher.embedding_source == "google" else ""
        
        return f"Successfully fetched {len(stars)} starred repositories for '{username}'{status}."
    except Exception as e:
        return f"Error in fetch_stars_tool: {str(e)}"

# Define search tool too
@mcp.tool(name="search_stars")
def search_stars_tool(username: str, query: str) -> str:
    """
    Search through a user's starred repositories using AI-powered semantic search or keyword matching.
    
    Args:
        username: The exact GitHub username provided by the user.
        query: The search terms or project idea to find relevant repositories for.
    """
    filename = f"{username}_stars.json"
    if not os.path.exists(filename):
        return f"Error: No data found for user '{username}'. Please run 'update_stars_for_user' first."
    
    try:
        searcher = StarSearcher(username)
        top = searcher.search(query, limit=5)
        
        if not top:
            return "No matches found."
            
        output = [f"--- Results for: {query} (via {searcher.embedding_source.upper()}) ---"]
        for repo in top:
            output.append(f"{repo['full_name']} | ★ {repo['stars']}")
            output.append(f"   {repo['url']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Error in search_stars_tool: {str(e)}"

if __name__ == "__main__":
    mcp.run()
