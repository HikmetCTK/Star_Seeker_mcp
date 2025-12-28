import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()
STAR_LIMIT = 10
def fetch_user_stars(username, token=None):
    """
    Fetches all starred repositories for a given public GitHub username.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    else:
        print(f"Note: No token provided. Using public access for user '{username}' (60 req/hr limit).")

    all_repos = []
    page = 1
    per_page = 100  # GitHub API limit

    print(f"Fetching starred repositories for user: {username}...")
    
    while True:
        # Always use the public endpoint for specific users
        url = f"https://api.github.com/users/{username}/starred?page={page}&per_page={per_page}"
        
        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            print(f"Network error: {e}")
            return []
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            try:
                print(response.json().get("message", ""))
            except:
                print(response.text)
            break

        data = response.json()
        
        if not data:
            break
        
        for repo in data:
            if repo.get("stargazers_count") < STAR_LIMIT: # Filter out repos with less than 100 stars
                continue
            all_repos.append({
                "full_name": repo.get("full_name"),
                "language": repo.get("language"),
                "description": repo.get("description"), # Keep raw None if missing, handle display later
                "url": repo.get("html_url"),
                "stars": repo.get("stargazers_count"),
                "topics": repo.get("topics", [])
            })
            
        print(f"Fetched page {page} ({len(data)} repos)")
        
        if len(data) < per_page:
            break
            
        break

    print(f"\nTotal starred repositories found: {len(all_repos)}")
    return all_repos

if __name__ == "__main__":
    # Interactive CLI Test
    target_user = input("Enter GitHub username to fetch stars for: ").strip()
    if target_user:
        # Try to load token from env just in case, but it's optional
        my_token = os.getenv("GITHUB_TOKEN")
        
        stars = fetch_user_stars(target_user, my_token)
        
        # Save to file for caching
        filename = f"{target_user}_stars1.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(stars, f, indent=4)
            
        print(f"Saved to {filename}")
