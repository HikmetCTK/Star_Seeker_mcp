"""
GitHub API client for fetching starred repositories.
"""

import requests
from config import logger

# Minimum number of stars for a repository to be included in the database
REPO_STAR_THRESHOLD = 10

def raw_fetch_user_stars(username, token=None):
    """
    Fetch all starred repositories for a GitHub user.
    
    Args:
        username (str): The GitHub username.
        token (str, optional): GitHub Personal Access Token for higher rate limits.
        
    Returns:
        list: A list of dicts containing repo metadata (name, language, description, etc.).
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token and str(token).strip().lower() not in ("none", ""):
        headers["Authorization"] = f"token {token}"
    
    all_repos = []
    page = 1
    per_page = 100 # Maximum allowed by GitHub API
    
    while True:
        url = f"https://api.github.com/users/{username}/starred?page={page}&per_page={per_page}"
        try:
            logger.info(f"Fetching GitHub stars for {username} - Page {page}")
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"GitHub API Error: {response.status_code} - {response.text}")
                break
                
            data = response.json()
            if not data:
                break
                
            for repo in data:
                # Filter out low-quality/obscure repositories
                if repo.get("stargazers_count", 0) < REPO_STAR_THRESHOLD:
                    continue
                    
                all_repos.append({
                    "full_name": repo.get("full_name"),
                    "language": repo.get("language"),
                    "description": repo.get("description"),
                    "url": repo.get("html_url"),
                    "stars": repo.get("stargazers_count"),
                    "topics": repo.get("topics", [])
                })
            
            # If we got fewer than per_page items, it's the last page
            if len(data) < per_page:
                break
                
            page += 1
            # Hard limit of 50 pages (5000 stars) to prevent infinite loops and rate limit exhaustion
            if page > 50: 
                break
        except Exception as e:
            logger.error(f"Unexpected error fetching stars: {str(e)}")
            break
            
    return all_repos
