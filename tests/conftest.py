import sys
from pathlib import Path

# Ensure the project root is on sys.path so tests can import modules like
# `github_client`, `search_engine`, and `server` when running via pytest.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


