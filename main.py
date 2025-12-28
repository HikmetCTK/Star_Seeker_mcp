import os
import fetch_stars
import search_tool

def main():
    print("=== GitHub Star Recommender ===")
    username = input("Enter GitHub Username: ").strip()
    
    if not username:
        print("Username is required.")
        return

    filename = f"{username}_stars.json"
    data_exists = os.path.exists(filename)
    
    should_fetch = False
    if not data_exists:
        print("First time setup: Downloading stars...")
        should_fetch = True
    else:
        refresh = input("Refresh data from GitHub? (y/n): ").lower()
        if refresh == 'y':
            should_fetch = True

    if should_fetch:
        # Optional: Load token if available
        token = os.getenv("GITHUB_TOKEN")
        stars = fetch_stars.fetch_user_stars(username, token)
        if stars:
            with open(filename, "w", encoding="utf-8") as f:
                import json
                json.dump(stars, f, indent=4)
            print(f"Data saved to {filename}")
        else:
            print("Failed to fetch stars. Exiting.")
            return

    # Start Search
    print("\nInitializing Search Engine...")
    searcher = search_tool.StarSearcher(filename)
    
    print(f"\nReady! I know about {len(searcher.repos)} tools in {username}'s library.")
    print("Tell me about your new project, and I'll recommend tools you've starred.")
    
    while True:
        query = input("\n> Project Idea (or 'q' to quit): ")
        if query.lower() in ['q', 'quit', 'exit']:
            break
            
        results_dict = searcher.search(query)
        
        for intent, recommendations in results_dict.items():
            print(f"\n--- Suggested Tools for: '{intent}' ---")
            if not recommendations:
                print("No close matches found.")
            
            for i, repo in enumerate(recommendations, 1):
                print(f"{i}. {repo['full_name']} | ★ {repo['stars']}")
                desc = repo['description'] or "No description"
                print(f"   {desc[:100]}...")
                print(f"   {repo['url']}")
            print("-" * 30)

if __name__ == "__main__":
    main()
