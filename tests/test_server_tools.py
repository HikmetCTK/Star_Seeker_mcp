import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from server import _fetch_stars_impl, _search_stars_impl, DATA_DIR


@patch("server.raw_fetch_user_stars")
@patch("server.StarSearcher")
def test_fetch_stars_tool_writes_json_and_triggers_searcher(mock_searcher_cls, mock_raw_fetch):
    username = "tooluser"
    stars = [
        {
            "full_name": "owner/repo1",
            "language": "Python",
            "description": "Test repo",
            "url": "https://github.com/owner/repo1",
            "stars": 42,
            "topics": [],
        }
    ]
    mock_raw_fetch.return_value = stars

    # Use a temporary directory under DATA_DIR to avoid interfering with real data
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    json_path = Path(DATA_DIR) / f"{username}_stars.json"
    if json_path.exists():
        json_path.unlink()

    # Test the implementation function directly (not the decorated wrapper)
    msg = _fetch_stars_impl(username, token="dummy")

    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        stored = json.load(f)
    assert stored == stars

    # Ensure StarSearcher is constructed for the given user
    mock_searcher_cls.assert_called_with(username)

    # Return message should mention number of stars
    assert "Successfully fetched 1 starred repositories" in msg


@patch("server.StarSearcher")
def test_search_stars_tool_returns_formatted_results(mock_searcher_cls):
    username = "searchuser"
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    json_path = Path(DATA_DIR) / f"{username}_stars.json"

    # Create a minimal JSON file so the tool considers the user valid
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([], f)

    mock_searcher = MagicMock()
    mock_searcher.embedding_source = "keyword"
    mock_searcher.search.return_value = [
        {
            "full_name": "owner/repo1",
            "url": "https://github.com/owner/repo1",
            "stars": 10,
            "description": "A test repository",
        }
    ]
    mock_searcher_cls.return_value = mock_searcher

    # Test the implementation function directly (not the decorated wrapper)
    output = _search_stars_impl(username, "test query")

    assert "--- Results for: test query (via KEYWORD) ---" in output
    assert "owner/repo1 | ★ 10" in output
    assert "A test repository" in output


def test_search_stars_tool_errors_when_no_data():
    username = "missinguser"
    json_path = Path(DATA_DIR) / f"{username}_stars.json"
    if json_path.exists():
        json_path.unlink()

    # Test the implementation function directly (not the decorated wrapper)
    msg = _search_stars_impl(username, "anything")
    assert "Error: No data found for user" in msg


