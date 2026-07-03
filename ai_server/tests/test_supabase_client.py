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


class TestDeleteStudentFromSupabase:
    def test_delete_student_success(self, mock_sb):
        from app.supabase_client import delete_student_from_supabase, SUPABASE_STORAGE_BUCKET
        
        # Mock database responses
        # First query: users select id
        mock_user_query = MagicMock()
        mock_user_query.eq.return_value.execute.return_value.data = [{"id": 100}]
        
        # Second query: user_images select image_path
        mock_img_query = MagicMock()
        mock_img_query.eq.return_value.execute.return_value.data = [
            {"image_path": "https://supabase.co/storage/v1/object/public/bucket/img1.jpg"},
            {"image_path": "https://supabase.co/storage/v1/object/public/bucket/img2.jpg"}
        ]
        
        # Third query: registration_queue select image_path
        mock_queue_query = MagicMock()
        mock_queue_query.eq.return_value.execute.return_value.data = [
            {"image_path": "https://supabase.co/storage/v1/object/public/bucket/img3.jpg"}
        ]
        
        # Delete queries
        mock_delete_query1 = MagicMock()
        mock_delete_query1.eq.return_value.execute.return_value = MagicMock()
        
        mock_delete_query2 = MagicMock()
        mock_delete_query2.eq.return_value.execute.return_value = MagicMock()

        # Storage mock
        mock_bucket = MagicMock()
        mock_sb.storage.from_.return_value = mock_bucket

        # Wire mock_sb.table to return our queries sequentially or by table name
        def table_mock_side_effect(table_name):
            if table_name == "users":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_user_query
                table_obj.delete.return_value = mock_delete_query1
                return table_obj
            elif table_name == "user_images":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_img_query
                return table_obj
            elif table_name == "registration_queue":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_queue_query
                table_obj.delete.return_value = mock_delete_query2
                return table_obj
            return MagicMock()

        mock_sb.table.side_effect = table_mock_side_effect

        # Call function
        res = delete_student_from_supabase("S001")

        # Verify
        assert res is True
        
        # Verify storage removal
        mock_sb.storage.from_.assert_called_with(SUPABASE_STORAGE_BUCKET)
        # Files should be img1.jpg, img2.jpg, img3.jpg in some order
        removed_files = mock_bucket.remove.call_args[0][0]
        assert set(removed_files) == {"img1.jpg", "img2.jpg", "img3.jpg"}

        # Verify DB deletes
        mock_delete_query1.eq.assert_called_with("student_id", "S001")
        mock_delete_query2.eq.assert_called_with("student_id", "S001")

    def test_delete_student_no_user(self, mock_sb):
        from app.supabase_client import delete_student_from_supabase
        
        # Mock database response where user doesn't exist
        mock_user_query = MagicMock()
        mock_user_query.eq.return_value.execute.return_value.data = []

        mock_queue_select = MagicMock()
        mock_queue_select.eq.return_value.execute.return_value.data = []

        mock_delete_query1 = MagicMock()
        mock_delete_query1.eq.return_value.execute.return_value = MagicMock()

        mock_delete_query2 = MagicMock()
        mock_delete_query2.eq.return_value.execute.return_value = MagicMock()

        def table_mock_side_effect(table_name):
            if table_name == "users":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_user_query
                table_obj.delete.return_value = mock_delete_query1
                return table_obj
            elif table_name == "registration_queue":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_queue_select
                table_obj.delete.return_value = mock_delete_query2
                return table_obj
            return MagicMock()

        mock_sb.table.side_effect = table_mock_side_effect

        res = delete_student_from_supabase("S999")
        assert res is True
        
        # Storage should NOT be called since user and queue didn't exist (no files)
        mock_sb.storage.from_.assert_not_called()

        # DB deletes should still be called to ensure any remaining records are cleared
        mock_delete_query1.eq.assert_called_with("student_id", "S999")
        mock_delete_query2.eq.assert_called_with("student_id", "S999")

    def test_delete_student_queue_only(self, mock_sb):
        from app.supabase_client import delete_student_from_supabase, SUPABASE_STORAGE_BUCKET
        
        # Mock database response where user doesn't exist
        mock_user_query = MagicMock()
        mock_user_query.eq.return_value.execute.return_value.data = []
        
        # registration_queue has pending items
        mock_queue_select = MagicMock()
        mock_queue_select.eq.return_value.execute.return_value.data = [
            {"image_path": "https://supabase.co/storage/v1/object/public/bucket/img_queue.jpg"}
        ]

        mock_delete_query1 = MagicMock()
        mock_delete_query1.eq.return_value.execute.return_value = MagicMock()

        mock_delete_query2 = MagicMock()
        mock_delete_query2.eq.return_value.execute.return_value = MagicMock()

        mock_bucket = MagicMock()
        mock_sb.storage.from_.return_value = mock_bucket

        def table_mock_side_effect(table_name):
            if table_name == "users":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_user_query
                table_obj.delete.return_value = mock_delete_query1
                return table_obj
            elif table_name == "registration_queue":
                table_obj = MagicMock()
                table_obj.select.return_value = mock_queue_select
                table_obj.delete.return_value = mock_delete_query2
                return table_obj
            return MagicMock()

        mock_sb.table.side_effect = table_mock_side_effect

        res = delete_student_from_supabase("S777")
        assert res is True
        
        # Storage should be called for the queue file
        mock_sb.storage.from_.assert_called_with(SUPABASE_STORAGE_BUCKET)
        removed_files = mock_bucket.remove.call_args[0][0]
        assert set(removed_files) == {"img_queue.jpg"}

        # DB deletes should still be called to ensure any remaining records are cleared
        mock_delete_query1.eq.assert_called_with("student_id", "S777")
        mock_delete_query2.eq.assert_called_with("student_id", "S777")



