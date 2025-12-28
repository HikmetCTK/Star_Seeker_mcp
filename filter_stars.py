import json

def filter_stars():
    input_file = "my_stars.json"
    output_file = "starred_repos_clean.json"
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            repos = json.load(f)
            
        filtered_repos = []
        for repo in repos:
            filtered_repos.append({
                "full_name": repo.get("full_name"),
                "description": repo.get("description"),
                "url": repo.get("html_url"),
                "stars": repo.get("stargazers_count")
            })
            
        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(filtered_repos, f, indent=4)
            
        print(f"Successfully processed {len(repos)} repositories.")
        print(f"Saved filtered data to {output_file}")
        
        # Print first 10 for immediate user view
        print("\n--- Preview (First 10) ---")
        for i, repo in enumerate(filtered_repos[:10]):
            print(f"{i+1}. {repo['full_name']}")
            print(f"   Stars: {repo['stars']}")
            print(f"   URL: {repo['url']}")
            print(f"   Desc: {repo['description']}")
            print("-" * 40)
            
    except FileNotFoundError:
        print(f"Error: {input_file} not found. Please run fetch_stars.py first.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    filter_stars()
