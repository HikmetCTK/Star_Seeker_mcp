import sys
import os
sys.path.append(os.getcwd())
import server

print(f"Type of search_stars: {type(server.search_stars)}")
print(f"Dir of search_stars: {dir(server.search_stars)}")
try:
    print("Trying to call .fn()...")
    if hasattr(server.search_stars, 'fn'):
        print(f"fn attribute exists: {server.search_stars.fn}")
except Exception as e:
    print(e)
