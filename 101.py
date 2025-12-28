import requests
import os 
from dotenv import load_dotenv
load_dotenv()
# Method 1: Public access
username = "HikmetCTK"
response = requests.get(f"https://api.github.com/users/{username}/starred")
starred_repos = response.json()

# Method 2: Authenticated (recommended)
headers = {
    "Authorization": "token " + os.getenv("GITHUB_TOKEN"),
    "Accept": "application/vnd.github.v3+json"
}
response = requests.get("https://api.github.com/user/starred", headers=headers)
starred_repos = response.json()

for repo in starred_repos:
    print(f"{repo['full_name']} - {repo['description']}")
    print(f"Language: {repo['language']}, Stars: {repo['stargazers_count']}")
    print(f"URL: {repo['html_url']}\n")