"""Regression tests for embedding-cache correctness.

Covers two failure modes found in StarSearcher:
  1. Stale cache: cache keyed on vector count only, so swapping repo descriptions
     for the same number of repos served vectors for the old corpus.
  2. Empty corpus: an empty embedding array is not None, so it was cached and
     served as a successful build, silently degrading search.
"""

import json
from pathlib import Path
from unittest import mock

import numpy as np
import pytest

import search_engine
from search_engine import StarSearcher


class _FakeEmbedding:
    def __init__(self, values):
        self.values = values


class _FakeResult:
    def __init__(self, vectors):
        self.embeddings = [_FakeEmbedding(v) for v in vectors]


class _FakeModels:
    def __init__(self, counter, dim=8):
        self.counter = counter
        self.dim = dim

    def embed_content(self, model=None, contents=None):
        self.counter["calls"] += 1
        items = [contents] if isinstance(contents, str) else list(contents)
        # Deterministic pseudo-embedding derived from the text itself, so a
        # fingerprint mismatch is observable.
        out = []
        for text in items:
            seed = sum(ord(c) for c in str(text))
            out.append([float((seed + i) % 97) for i in range(self.dim)])
        return _FakeResult(out)


class _FakeClient:
    def __init__(self, counter):
        self.models = _FakeModels(counter)


def _write_stars(tmp_path, username, descriptions):
    repos = [
        {
            "full_name": f"owner/repo{i}",
            "language": "Python",
            "description": d,
            "url": f"https://github.com/owner/repo{i}",
            "stars": 100 + i,
            "topics": [],
        }
        for i, d in enumerate(descriptions)
    ]
    path = tmp_path / f"{username}_stars.json"
    path.write_text(json.dumps(repos), encoding="utf-8")
    return path


def _make_searcher(tmp_path, username, counter):
    """Build a searcher with the fake client already in place.

    StarSearcher.__init__ calls load_data(), which calls _load_or_build_embeddings().
    The client therefore has to exist before construction, otherwise the first
    build runs with no client and is discarded.
    """
    with mock.patch.object(StarSearcher, "_load_or_build_embeddings", lambda self: None):
        searcher = StarSearcher(username)
    searcher.embedding_source = "google"
    searcher.google_client = _FakeClient(counter)
    searcher.json_path = str(tmp_path / f"{username}_stars.json")
    searcher.cache_path = str(tmp_path / f"{username}_stars_embeddings.pkl")
    return searcher


def test_cold_build_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(search_engine, "DATA_DIR", tmp_path)
    _write_stars(tmp_path, "user", [f"alpha repo {i}" for i in range(5)])
    counter = {"calls": 0}
    s = _make_searcher(tmp_path, "user", counter)

    s._load_or_build_embeddings()

    assert counter["calls"] == 1
    assert s.embeddings is not None
    assert len(s.embeddings) == 5
    assert Path(s.cache_path).exists()


def test_warm_load_uses_cache_without_api_call(tmp_path, monkeypatch):
    monkeypatch.setattr(search_engine, "DATA_DIR", tmp_path)
    _write_stars(tmp_path, "user", [f"alpha repo {i}" for i in range(5)])
    counter = {"calls": 0}

    first = _make_searcher(tmp_path, "user", counter)
    first._load_or_build_embeddings()
    calls_after_first = counter["calls"]

    second = _make_searcher(tmp_path, "user", counter)
    second._load_or_build_embeddings()

    assert counter["calls"] == calls_after_first, "warm load should not call the API"
    assert len(second.embeddings) == 5


def test_cache_invalidated_when_descriptions_change_same_count(tmp_path, monkeypatch):
    """Regression: same repo count but different content must invalidate the cache."""
    monkeypatch.setattr(search_engine, "DATA_DIR", tmp_path)
    _write_stars(tmp_path, "user", [f"alpha repo {i}" for i in range(5)])
    counter = {"calls": 0}
    first = _make_searcher(tmp_path, "user", counter)
    first._load_or_build_embeddings()
    first_vectors = np.array(first.embeddings)
    calls_before = counter["calls"]

    # Swap in completely different descriptions, same number of repos.
    _write_stars(tmp_path, "user", [f"omega project {i}" for i in range(5)])
    second = _make_searcher(tmp_path, "user", counter)
    second._load_or_build_embeddings()

    assert counter["calls"] > calls_before, "stale cache was served after corpus changed"
    assert not np.array_equal(np.array(second.embeddings), first_vectors)


def test_empty_corpus_is_not_treated_as_success(tmp_path, monkeypatch):
    """Regression: an empty embedding array was cached and served as a valid build."""
    monkeypatch.setattr(search_engine, "DATA_DIR", tmp_path)
    _write_stars(tmp_path, "empty", [])
    counter = {"calls": 0}
    s = _make_searcher(tmp_path, "empty", counter)

    s._load_or_build_embeddings()

    assert s.embeddings is None, "empty corpus must not produce embeddings"
    assert not Path(s.cache_path).exists(), "empty result must not be cached"


def test_failed_embedding_batch_is_not_cached(tmp_path, monkeypatch):
    """A mid-batch API failure returns None today, and must not poison the cache."""
    monkeypatch.setattr(search_engine, "DATA_DIR", tmp_path)
    _write_stars(tmp_path, "user", [f"alpha repo {i}" for i in range(5)])
    counter = {"calls": 0}
    s = _make_searcher(tmp_path, "user", counter)

    def _boom(**_kwargs):
        counter["calls"] += 1
        raise RuntimeError("simulated API failure")

    s.google_client.models.embed_content = _boom
    s._load_or_build_embeddings()

    assert s.embeddings is None
    assert not Path(s.cache_path).exists()


def test_search_falls_back_to_bm25_when_embeddings_missing(tmp_path, monkeypatch):
    """With no embeddings, search must still work through the BM25 path."""
    monkeypatch.setattr(search_engine, "DATA_DIR", tmp_path)
    descriptions = [
        "vector database for similarity search",
        "kubernetes operator for cluster management",
        "postgres migration toolkit",
    ]
    _write_stars(tmp_path, "user", descriptions)
    counter = {"calls": 0}
    s = _make_searcher(tmp_path, "user", counter)

    s.embeddings = None
    s.load_data()
    s.embeddings = None

    results = s.search("kubernetes cluster", limit=3)

    assert results, "BM25 fallback should still return results"
    assert "kubernetes" in results[0]["description"].lower()
