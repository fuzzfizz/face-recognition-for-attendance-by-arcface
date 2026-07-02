"""Tests for ai_server.app.supabase_client fixes (Task 3)."""
from unittest.mock import MagicMock, patch

import pytest

from app.supabase_client import (
    get_pending_queue_items,
    upsert_user,
)


@pytest.fixture(autouse=True)
def _enable_supabase(monkeypatch):
    """Make is_available() return True so we test the Supabase paths."""
    monkeypatch.setattr("app.supabase_client.SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr("app.supabase_client.SUPABASE_KEY", "fake-key")


@pytest.fixture()
def mock_sb():
    """Return a mock Supabase client and patch get_supabase to use it."""
    client = MagicMock()
    with patch("app.supabase_client.get_supabase", return_value=client):
        yield client


# ── get_pending_queue_items ──────────────────────────────────────────


class TestGetPendingQueueItems:
    def test_returns_pending_items(self, mock_sb):
        fake_items = [
            {"id": 1, "student_id": "S001", "image_path": "/img/1.jpg", "status": "pending"},
            {"id": 2, "student_id": "S002", "image_path": "/img/2.jpg", "status": "pending"},
        ]
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=fake_items)

        result = get_pending_queue_items()

        mock_sb.table.assert_called_with("registration_queue")
        mock_sb.table().select.assert_called_with("*")
        mock_sb.table().select().eq.assert_called_with("status", "pending")
        assert result == fake_items

    def test_returns_empty_list_when_no_pending(self, mock_sb):
        (
            mock_sb.table.return_value
            .select.return_value
            .eq.return_value
            .execute.return_value
        ) = MagicMock(data=[])

        result = get_pending_queue_items()
        assert result == []

    def test_returns_empty_on_supabase_error(self, mock_sb):
        mock_sb.table.side_effect = Exception("network error")
        result = get_pending_queue_items()
        assert result == []


# ── upsert_user ──────────────────────────────────────────────────────


class TestUpsertUser:
    def test_uses_atomic_upsert_with_on_conflict(self, mock_sb):
        fake_user = {"id": 1, "student_id": "S001"}
        (
            mock_sb.table.return_value
            .upsert.return_value
            .execute.return_value
        ) = MagicMock(data=[fake_user])

        result = upsert_user("S001")

        mock_sb.table.assert_called_with("users")
        mock_sb.table().upsert.assert_called_with(
            {"student_id": "S001"}, on_conflict="student_id"
        )
        assert result == fake_user

    def test_uses_atomic_upsert_with_name(self, mock_sb):
        fake_user = {"id": 1, "student_id": "S001", "name": "John Doe"}
        (
            mock_sb.table.return_value
            .upsert.return_value
            .execute.return_value
        ) = MagicMock(data=[fake_user])

        result = upsert_user("S001", "John Doe")

        mock_sb.table.assert_called_with("users")
        mock_sb.table().upsert.assert_called_with(
            {"student_id": "S001", "name": "John Doe"}, on_conflict="student_id"
        )
        assert result == fake_user

    def test_returns_none_on_empty_response(self, mock_sb):
        (
            mock_sb.table.return_value
            .upsert.return_value
            .execute.return_value
        ) = MagicMock(data=[])

        result = upsert_user("S002")
        assert result is None

    def test_returns_none_on_error(self, mock_sb):
        mock_sb.table.side_effect = Exception("db error")
        result = upsert_user("S003")
        assert result is None


# ── get_pending_queue_items with limit ────────────────────────────────

def test_get_pending_queue_items_with_limit(mock_sb):
    from app.supabase_client import get_pending_queue_items
    mock_sb.table().select().eq().limit().execute.return_value.data = [{"id": 1}]
    res = get_pending_queue_items(limit=5)
    assert len(res) == 1
    mock_sb.table.assert_called_with("registration_queue")
    mock_sb.table().select.assert_called_with("*")
    mock_sb.table().select().eq.assert_called_with("status", "pending")
    mock_sb.table().select().eq().limit.assert_called_with(5)


# ── get_latest_check_in_log ───────────────────────────────────────────

def test_get_latest_check_in_log(mock_sb):
    from app.supabase_client import get_latest_check_in_log
    mock_sb.table().select().eq().order().limit().execute.return_value.data = [{"id": 42, "student_id": "S123", "timestamp": "2026-07-02T12:00:00Z"}]
    res = get_latest_check_in_log("S123")
    assert res["id"] == 42
    mock_sb.table.assert_called_with("check_in_logs")
    mock_sb.table().select.assert_called_with("*")
    mock_sb.table().select().eq.assert_called_with("student_id", "S123")
    mock_sb.table().select().eq().order.assert_called_with("timestamp", desc=True)
    mock_sb.table().select().eq().order().limit.assert_called_with(1)

