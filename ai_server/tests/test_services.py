"""Tests for service layer (Task 8)."""
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Mock insightface.app before importing FaceProcessor
sys.modules["insightface"] = MagicMock()
sys.modules["insightface.app"] = MagicMock()

import pytest
from fastapi import UploadFile, HTTPException

from app.services.registration_service import register_images, get_registration_status
from app.services.training_service import process_pending_queue
from app.services.verification_service import verify_face


# ── Registration Service ─────────────────────────────────────────────

@pytest.mark.anyio
@patch("app.services.registration_service.upsert_user")
@patch("app.services.registration_service.upload_image")
@patch("app.services.registration_service.insert_queue_item")
async def test_register_images_success(mock_insert_queue, mock_upload_image, mock_upsert_user):
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    mock_upload_image.return_value = "http://storage.co/img.jpg"

    # Create mock UploadFile
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"image_content")

    result = await register_images("S123", [mock_file])

    mock_upsert_user.assert_called_once_with("S123")
    mock_upload_image.assert_called_once_with(b"image_content", "S123", "jpg")
    mock_insert_queue.assert_called_once_with("S123", "http://storage.co/img.jpg")
    assert result["status"] == "pending"
    assert result["student_id"] == "S123"

@patch("app.services.registration_service.get_user_by_student_id")
@patch("app.services.registration_service.get_all_embeddings")
def test_get_registration_status_completed(mock_get_all_embeddings, mock_get_user):
    mock_get_user.return_value = {"id": 1, "student_id": "S123"}
    mock_get_all_embeddings.return_value = [{"student_id": "S123", "embeddings": []}]

    result = get_registration_status("S123")
    assert result["status"] == "completed"
    assert "Face extracted and saved successfully" in result["message"]


# ── Training Service ─────────────────────────────────────────────────

@patch("app.services.training_service.get_pending_queue_items")
@patch("app.services.training_service.get_face_processor")
@patch("app.services.training_service.update_queue_item_status")
@patch("app.services.training_service.get_all_embeddings")
@patch("app.services.training_service.save_all_embeddings")
@patch("app.services.training_service.invalidate_cache")
def test_process_pending_queue_success(
    mock_invalidate, mock_save, mock_get_all, mock_update_status, mock_get_processor, mock_get_pending
):
    mock_get_pending.return_value = [
        {"id": 1, "student_id": "S123", "image_path": "/path/1.jpg"}
    ]
    
    mock_processor = MagicMock()
    mock_processor.decode_image_path.return_value = MagicMock()
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor

    mock_get_all.return_value = []

    result = process_pending_queue()

    mock_get_pending.assert_called_once()
    mock_processor.decode_image_path.assert_called_once_with("/path/1.jpg")
    mock_processor.extract_face_embedding.assert_called_once()
    mock_update_status.assert_called_once_with(1, "completed")
    mock_save.assert_called_once()
    mock_invalidate.assert_called_once()
    assert result["message"] == "Training completed"
    assert "S123" in result["processed_students"]


# ── Verification Service ─────────────────────────────────────────────

@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.insert_log")
def test_verify_face_match(mock_insert_log, mock_match, mock_decode, mock_get_processor):
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor

    mock_match.return_value = {"student_id": "S123", "similarity": 0.85, "user_id": 1}

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    mock_decode.assert_called_once_with(b"image_bytes")
    mock_match.assert_called_once_with([0.1] * 512)
    mock_insert_log.assert_called_once_with(
        student_id="S123", similarity_score=0.85, device_id="ESP-TEST", user_id=1
    )
    assert result["match"] is True
    assert result["student_id"] == "S123"
    assert result["similarity_score"] == 0.85
