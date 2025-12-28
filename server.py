print("--- REFRESHED SERVER STARTING ---")
from fastmcp import FastMCP
import os
import json
from fetch_stars import fetch_user_stars as github_fetch_user_stars
import search_tool

# Initialize FastMCP
mcp = FastMCP("GitHub Stars Recommender")

# Cache for searchers to avoid reloading embeddings heavily
# Key: username -> Value: StarSearcher instance
searcher_cache = {}

# Logic Functions (Testable)
def fetch_stars_logic(username: str, token: str = None) -> str:
    """Core logic for fetching stars."""
    # Use provided token or fallback to environment variable
    api_token = token or os.getenv("GITHUB_TOKEN")
    
    try:
        stars = github_fetch_user_stars(username, api_token)
        
        # Save to file (matching existing logic)
        filename = f"{username}_stars.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(stars, f, indent=4)
            
        # Invalidate cache for this user since data changed
        if username in searcher_cache:
            del searcher_cache[username]
            
        return f"Successfully fetched {len(stars)} starred repositories for '{username}'. Data saved to {filename}."
    except Exception as e:
        return f"Error fetching stars: {str(e)}"

def search_stars_logic(username: str, query: str) -> str:
    """Core logic for searching stars."""
    filename = f"{username}_stars.json"
    
    if not os.path.exists(filename):
        return f"Error: No data found for user '{username}'. Please run 'fetch_stars' first."
        
    try:
        # Load or retrieve cached searcher
        if username not in searcher_cache:
            # This might take a moment to load embeddings
            searcher_cache[username] = search_tool.StarSearcher(filename)
            
        searcher = searcher_cache[username]

        # Use the search method
        results_dict = searcher.search(query)
        
        # Format output string
        output = []
        for intent, recommendations in results_dict.items():
            output.append(f"--- Suggested Tools for: '{intent}' ---")
            if not recommendations:
                output.append("No close matches found.")
            
            for i, repo in enumerate(recommendations, 1):
                stars = repo.get('stars', 'N/A')
                desc = repo.get('description') or "No description"
                output.append(f"{i}. {repo['full_name']} | ★ {stars}")
                output.append(f"   {desc[:100]}...")
                output.append(f"   {repo['url']}\n")
                
        return "\n".join(output)
        
    except Exception as e:
        return f"Error performing search: {str(e)}"

# MCP Tools
@mcp.tool
def fetch_stars(username: str, token: str = None) -> str:
    """
    Fetch or update starred repositories for a given GitHub username. Do not forget to get username from user.
    
    Args:
        username: The GitHub username to fetch stars for.
        token: Optional GitHub personal access token (increases rate limits). 
               Defaults to looking for GITHUB_TOKEN env var if not provided.
    """
    return fetch_stars_logic(username, token)

@mcp.tool
def search_stars(username: str, query: str) -> str:
    """
    Search through a user's starred repositories using semantic or keyword search.
    
    Args:
        username: The GitHub username whose stars to search.
        query: The project idea or search query (e.g., "python web framework").
    """
    return search_stars_logic(username, query)

if __name__ == "__main__":
    mcp.run()
