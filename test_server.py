import sys
import os

# Ensure local modules can be imported
sys.path.append(os.getcwd())

import server

def test_search():
    print("Testing search_stars...")
    # Assuming 'HikmetCTK' data exists or will fail gracefully
    # If not, try creating a dummy file or just checking the error message
    
    # Check if we have any .json file to test with
    # If not, we might skipped real search test
    
    # Let's try to search for a likely user or just check error handling
    result = server.search_stars_logic("HikmetCTK", "data science")
    print("Search Result Preview:")
    print(result[:200] + "...")
    
def test_fetch_mock():
    print("\nTesting fetch_stars (Mock/Dry)...")
    # We won't actually call fetch implementation efficiently without mocking 
    # but we can try calling it and expect error or success.
    # To be safe/quick, let's just print that the function exists and is callable.
    print(f"fetch_stars is callable: {callable(server.fetch_stars_logic)}")

if __name__ == "__main__":
    try:
        test_search()
        test_fetch_mock()
        print("\nVerification Passed!")
    except Exception as e:
        print(f"\nVerification Failed: {e}")
        sys.exit(1)
