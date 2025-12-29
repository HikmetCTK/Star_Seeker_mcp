"""
FastMCP Server implementation for the GitHub Stars Recommender.
Exposes tools for fetching and searching starred repositories.
"""

from fastmcp import FastMCP
import os
import json
from config import get_data_dir, get_system_prompt, logger
from github_client import raw_fetch_user_stars
from search_engine import StarSearcher
import sys

# Ensure logger is initialized (fallback for edge cases)
if 'logger' not in globals():
    import logging
    logger = logging.getLogger(__name__)

DATA_DIR = get_data_dir()
SYSTEM_PROMPT = get_system_prompt()

# Initialize FastMCP Server
# instructions: Help the model understand its role and how to use tools.
mcp = FastMCP("StarSeeker", instructions=SYSTEM_PROMPT)


# Core implementation functions (testable without FastMCP decorator)
def _fetch_stars_impl(username: str, token: str = None) -> str:
    """
    Core implementation for fetching stars. Extracted for testability.
    
    Args:
        username: The exact GitHub username (e.g., 'gulbaki').
        token: Optional GitHub personal access token to avoid rate limits (defaults to GITHUB_TOKEN env).
    """
    api_token = token or os.getenv("GITHUB_TOKEN")
    try:
        # 1. Fetch from GitHub API
        stars = raw_fetch_user_stars(username, api_token)
        
        # 2. Save to local JSON storage
        filename = str(DATA_DIR / f"{username}_stars.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(stars, f, indent=4)
        
        # 3. Trigger embedding generation/update
        # This pre-calculates embeddings so subsequent searches are fast.
        searcher = StarSearcher(username)
        status = " (Embedded with Gemini)" if searcher.embedding_source == "google" else ""
        
        logger.info(f"Updated star database for {username}. Stars: {len(stars)}{status}")
        return f"Successfully fetched {len(stars)} starred repositories for '{username}'{status}."
    except Exception as e:
        logger.error(f"Error in fetch_stars_tool: {str(e)}")
        return f"Error in fetch_stars_tool: {str(e)}"


def _search_stars_impl(username: str, query: str) -> str:
    """
    Core implementation for searching stars. Extracted for testability.
    
    Args:
        username: The exact GitHub username provided by the user.
        query: The search terms or project idea to find relevant repositories for.
    """
    filename = str(DATA_DIR / f"{username}_stars.json")
    
    # Check if data exists locally
    if not os.path.exists(filename):
        return f"Error: No data found for user '{username}'. Please run 'fetch_stars_for_user' first."
    
    try:
        logger.info(f"Searching stars for {username}. Query: {query}")
        
        # Initialize searcher (will automatically load data and embeddings)
        searcher = StarSearcher(username)
        
        # Perform Search (Method depends on Gemini availability: Hybrid vs BM25 vs Keyword)
        top = searcher.search(query, limit=5)
        
        if not top:
            return "No matches found."
            
        # Format results for the AI model to read
        output = [f"--- Results for: {query} (via {searcher.embedding_source.upper()}) ---"]
        for repo in top:
            output.append(f"{repo['full_name']} | ★ {repo['stars']}")
            output.append(f"   {repo['url']}")
            # Add snippet of description if available
            desc = repo.get('description') or 'No description'
            output.append(f"   {desc[:150]}...\n")
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error in search_stars_tool: {str(e)}")
        return f"Error in search_stars_tool: {str(e)}"


# FastMCP decorated functions (wrappers around implementation)
@mcp.tool(name="_fetch_stars_for_user")
def fetch_stars_tool(username: str, token: str = None) -> str:
    """
    Fetch or update the database of starred repositories for a specific GitHub username.
    
    Args:
        username: The exact GitHub username (e.g., 'gulbaki').
        token: Optional GitHub personal access token to avoid rate limits (defaults to GITHUB_TOKEN env).
    """
    return _fetch_stars_impl(username, token)


@mcp.tool(name="search_stars")
def search_stars_tool(username: str, query: str) -> str:
    """
    Search through a user's starred repositories using AI-powered semantic search or keyword matching.
    
    Args:
        username: The exact GitHub username provided by the user.
        query: The search terms or project idea to find relevant repositories for.
    """
    return _search_stars_impl(username, query)

def run():
    """Entry point for the MCP server."""
    mcp.run()

