import json
import os
from pathlib import Path

from search_engine import StarSearcher, DATA_DIR


def setup_user_data(tmp_path: Path, username: str = "testuser"):
    """
    Helper to create a minimal stars JSON file for a fake user.
    It writes directly into search_engine.DATA_DIR so the production
    code can find it without modification.
    """
    # Ensure DATA_DIR exists
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    repos = [
        {
            "full_name": "owner/python-ml-project",
            "language": "Python",
            "description": "A machine learning project in Python using scikit-learn.",
            "url": "https://github.com/owner/python-ml-project",
            "stars": 150,
            "topics": ["machine-learning", "python"],
        },
        {
            "full_name": "owner/javascript-ui",
            "language": "JavaScript",
            "description": "A modern UI library for building web apps.",
            "url": "https://github.com/owner/javascript-ui",
            "stars": 200,
            "topics": ["frontend", "ui"],
        },
        {
            "full_name": "owner/random-repo",
            "language": "Go",
            "description": "Misc utilities.",
            "url": "https://github.com/owner/random-repo",
            "stars": 50,
            "topics": [],
        },
    ]

    json_path = Path(DATA_DIR) / f"{username}_stars.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(repos, f)

    return username


def test_simple_keyword_search_finds_relevant_repos(tmp_path, monkeypatch):
    username = setup_user_data(tmp_path)

    # Force StarSearcher to avoid Google embeddings to keep the test offline
    monkeypatch.setenv("GEMINI_API_KEY", "")

    searcher = StarSearcher(username)

    results = searcher.simple_keyword_search("python machine learning", limit=5)
    names = [r["full_name"] for r in results]

    assert "owner/python-ml-project" in names
    # Should not return anything clearly unrelated if there is a better match
    assert len(results) >= 1


def test_bm25_search_orders_more_relevant_repo_first(tmp_path, monkeypatch):
    username = setup_user_data(tmp_path)

    # Disable Google embeddings for deterministic keyword-only behaviour
    monkeypatch.setenv("GEMINI_API_KEY", "")

    searcher = StarSearcher(username)

    # BM25 should rank the Python ML project above others for this query
    results = searcher.bm25_search("python machine learning", limit=2)
    assert results
    assert results[0]["full_name"] == "owner/python-ml-project"


def test_search_falls_back_to_simple_keyword_when_no_indices(tmp_path, monkeypatch):
    """
    When there is no JSON file, search() should not crash and should
    fall back to the simple keyword search path, returning an empty list.
    """
    # Ensure there is no data for this user
    username = "no_data_user"
    json_path = Path(DATA_DIR) / f"{username}_stars.json"
    if json_path.exists():
        os.remove(json_path)

    monkeypatch.setenv("GEMINI_API_KEY", "")

    searcher = StarSearcher(username)
    results = searcher.search("anything", limit=5)

    assert isinstance(results, list)
    assert results == []


