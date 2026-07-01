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
