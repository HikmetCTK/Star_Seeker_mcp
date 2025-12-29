import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest

from server import _fetch_stars_impl, DATA_DIR
from github_client import raw_fetch_user_stars

@pytest.fixture
def clean_env():
    """Fixture to ensure GITHUB_TOKEN is not in the environment."""
    with patch.dict(os.environ, {}, clear=True):
        yield

@patch("github_client.requests.get")
def test_raw_fetch_user_stars_without_token(mock_get):
    """
    Test that raw_fetch_user_stars correctly omits the Authorization header
    when no token is provided.
    """
    username = "testuser"
    
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_get.return_value = mock_response
    
    # Call without token
    raw_fetch_user_stars(username, token=None)
    
    # Verify requests.get was called
    assert mock_get.called
    args, kwargs = mock_get.call_args
    headers = kwargs.get("headers", {})
    
    # Authorization header should NOT be present
    assert "Authorization" not in headers
    # Accept header should still be there
    assert headers.get("Accept") == "application/vnd.github.v3+json"

@patch("server.raw_fetch_user_stars")
@patch("server.StarSearcher")
def test_fetch_stars_impl_without_token_arg_and_no_env(mock_searcher_cls, mock_raw_fetch, clean_env):
    """
    Test that _fetch_stars_impl works correctly even if the user
    doesn't provide a token and GITHUB_TOKEN is not in environment.
    """
    username = "notokenuser"
    mock_raw_fetch.return_value = [
        {
            "full_name": "owner/repo1",
            "language": "Python",
            "description": "Test repo",
            "url": "https://github.com/owner/repo1",
            "stars": 100,
            "topics": [],
        }
    ]
    
    # Ensure data directory exists
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    json_path = Path(DATA_DIR) / f"{username}_stars.json"
    if json_path.exists():
        json_path.unlink()
    
    # Mock searcher
    mock_searcher = MagicMock()
    mock_searcher.embedding_source = "keyword"
    mock_searcher_cls.return_value = mock_searcher
    
    # Call implementation without token arg
    # GITHUB_TOKEN env is cleared by clean_env fixture
    msg = _fetch_stars_impl(username, token=None)
    
    # Verify successful completion
    assert "Successfully fetched 1 starred repositories" in msg
    assert json_path.exists()
    
    # Verify raw_fetch_user_stars was called with token=None
    mock_raw_fetch.assert_called_with(username, None)
