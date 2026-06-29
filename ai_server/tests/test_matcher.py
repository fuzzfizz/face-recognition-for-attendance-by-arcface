"""Tests for ai_server.app.matcher (Task 4)."""
import pickle
import time

import numpy as np
import pytest

from app import matcher
from app.matcher import invalidate_cache, load_embeddings, match_face


@pytest.fixture(autouse=True)
def _reset_cache():
    """Ensure every test starts with a clean cache."""
    invalidate_cache()
    yield
    invalidate_cache()


def _write_pkl(path, data):
    """Helper: write *data* to a pickle file at *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(data, f)


def _sample_embedding(seed: int = 0) -> list:
    """Return a deterministic L2-normalised 512-d embedding."""
    rng = np.random.RandomState(seed)
    vec = rng.randn(512).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec.tolist()


# ── load_embeddings + cache ──────────────────────────────────────────


class TestLoadEmbeddings:
    def test_returns_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", tmp_path / "missing.pkl")
        assert load_embeddings() == []

    def test_loads_data(self, tmp_path, monkeypatch):
        pkl = tmp_path / "face.pkl"
        data = [{"user_id": "1", "name": "Alice", "student_id": "S001", "embeddings": []}]
        _write_pkl(pkl, data)
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", pkl)

        result = load_embeddings()
        assert result == data

    def test_cache_avoids_second_read(self, tmp_path, monkeypatch):
        pkl = tmp_path / "face.pkl"
        data = [{"user_id": "1", "name": "A", "student_id": "S001", "embeddings": []}]
        _write_pkl(pkl, data)
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", pkl)

        first = load_embeddings()
        # Overwrite file with different data, but don't change mtime
        second = load_embeddings()
        assert first is second  # same object → cache hit

    def test_invalidate_causes_reload(self, tmp_path, monkeypatch):
        pkl = tmp_path / "face.pkl"
        data1 = [{"user_id": "1", "name": "A", "student_id": "S001", "embeddings": []}]
        _write_pkl(pkl, data1)
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", pkl)

        load_embeddings()
        invalidate_cache()

        data2 = [{"user_id": "2", "name": "B", "student_id": "S002", "embeddings": []}]
        _write_pkl(pkl, data2)

        result = load_embeddings()
        assert result == data2


# ── match_face ───────────────────────────────────────────────────────


class TestMatchFace:
    def test_returns_none_on_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", tmp_path / "missing.pkl")
        assert match_face(_sample_embedding(0)) is None

    def test_match_returns_student_id(self, tmp_path, monkeypatch):
        emb = _sample_embedding(42)
        pkl = tmp_path / "face.pkl"
        data = [{
            "user_id": "u1",
            "name": "Alice",
            "student_id": "S001",
            "embeddings": [emb],
        }]
        _write_pkl(pkl, data)
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", pkl)
        monkeypatch.setattr(matcher, "SIMILARITY_THRESHOLD", 0.5)

        result = match_face(emb)
        assert result is not None
        assert "student_id" in result
        assert result["student_id"] == "S001"
        assert result["similarity"] == pytest.approx(1.0, abs=0.01)

    def test_student_id_falls_back_to_name(self, tmp_path, monkeypatch):
        """When student_id is missing from the embedding dict, fall back to name."""
        emb = _sample_embedding(7)
        pkl = tmp_path / "face.pkl"
        data = [{
            "user_id": "u2",
            "name": "Bob",
            # no student_id key
            "embeddings": [emb],
        }]
        _write_pkl(pkl, data)
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", pkl)
        monkeypatch.setattr(matcher, "SIMILARITY_THRESHOLD", 0.5)

        result = match_face(emb)
        assert result is not None
        assert result["student_id"] == "Bob"

    def test_no_match_below_threshold(self, tmp_path, monkeypatch):
        emb_stored = _sample_embedding(0)
        emb_query = _sample_embedding(999)  # very different
        pkl = tmp_path / "face.pkl"
        data = [{
            "user_id": "u1",
            "name": "Alice",
            "student_id": "S001",
            "embeddings": [emb_stored],
        }]
        _write_pkl(pkl, data)
        monkeypatch.setattr(matcher, "EMBEDDINGS_PATH", pkl)
        monkeypatch.setattr(matcher, "SIMILARITY_THRESHOLD", 0.99)

        result = match_face(emb_query)
        assert result is None
