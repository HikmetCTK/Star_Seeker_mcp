from server import fetch_stars_logic
print("Attempting to call fetch_stars_logic...")
try:
    result = fetch_stars_logic("HikmetCTK")
    print(f"Result: {result}")
except Exception as e:
    print(f"Caught error: {e}")
