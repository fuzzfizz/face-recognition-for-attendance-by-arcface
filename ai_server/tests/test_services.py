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
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
@patch("app.services.registration_service.upload_image")
@patch("app.services.registration_service.insert_queue_item")
async def test_register_images_success(
    mock_insert_queue, mock_upload_image, mock_upsert_user, mock_get_processor
):
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    mock_upload_image.return_value = "http://storage.co/img.jpg"

    mock_processor = MagicMock()
    mock_processor.decode_image.return_value = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "failed_step": None,
        "error_message": None,
        "results": {
            "face_detected": True,
            "single_face": True
        }
    }
    mock_get_processor.return_value = mock_processor

    # Create mock UploadFile
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"image_content")

    result = await register_images("S123", "John Doe", [mock_file])

    mock_upsert_user.assert_called_once_with("S123", "John Doe")
    mock_upload_image.assert_called_once_with(b"image_content", "S123", "jpg")
    mock_insert_queue.assert_called_once_with("S123", "http://storage.co/img.jpg")
    assert result["status"] == "pending"
    assert result["student_id"] == "S123"

@pytest.mark.anyio
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_cannot_parse(
    mock_upsert_user, mock_get_processor
):
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    
    mock_processor = MagicMock()
    mock_processor.decode_image.return_value = None
    mock_get_processor.return_value = mock_processor

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"invalid_bytes")

    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", [mock_file])
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == "Some photos failed face verification."
    assert exc_info.value.detail["results"][0]["error"] == "Cannot parse image file"

@pytest.mark.anyio
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_no_face(
    mock_upsert_user, mock_get_processor
):
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    
    mock_processor = MagicMock()
    mock_processor.decode_image.return_value = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": False,
        "failed_step": 1,
        "error_message": "Please look at the camera",
        "results": {
            "face_detected": False,
            "single_face": False
        }
    }
    mock_get_processor.return_value = mock_processor

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"no_face_bytes")

    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", [mock_file])
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == "Some photos failed face verification."
    assert exc_info.value.detail["results"][0]["error"] == "Face not found, please retake"

@pytest.mark.anyio
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_multiple_faces(
    mock_upsert_user, mock_get_processor
):
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    
    mock_processor = MagicMock()
    mock_processor.decode_image.return_value = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": False,
        "failed_step": 2,
        "error_message": "One person at a time",
        "results": {
            "face_detected": True,
            "single_face": False
        }
    }
    mock_get_processor.return_value = mock_processor

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"multiple_faces_bytes")

    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", [mock_file])
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == "Some photos failed face verification."
    assert exc_info.value.detail["results"][0]["error"] == "Multiple faces in frame"

@pytest.mark.anyio
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_empty_file(
    mock_upsert_user, mock_get_processor
):
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    
    mock_processor = MagicMock()
    mock_get_processor.return_value = mock_processor

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"")

    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", [mock_file])
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["message"] == "Some photos failed face verification."
    assert exc_info.value.detail["results"][0]["error"] == "Empty upload file"
    assert exc_info.value.detail["results"][0]["validation_checklist"]["database_match"] is None


@pytest.mark.anyio
@patch("app.services.registration_service.get_pending_queue_items")
@patch("app.services.registration_service.get_all_embeddings")
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_quota_already_full(
    mock_upsert_user, mock_get_processor, mock_get_all_embeddings, mock_get_pending_queue_items
):
    # Student S123 has 5 registered embeddings and 5 pending queue records (total = 10)
    mock_get_all_embeddings.return_value = [
        {
            "student_id": "S123",
            "embeddings": [[0.1] * 512] * 5
        }
    ]
    mock_get_pending_queue_items.return_value = [
        {"student_id": "S123", "image_path": "/path/1.jpg"},
        {"student_id": "S123", "image_path": "/path/2.jpg"},
        {"student_id": "S123", "image_path": "/path/3.jpg"},
        {"student_id": "S123", "image_path": "/path/4.jpg"},
        {"student_id": "S123", "image_path": "/path/5.jpg"},
        {"student_id": "S456", "image_path": "/path/other.jpg"},
    ]
    
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"image_content")
    
    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", [mock_file])
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Already registered 10 photos (Quota full)"


@pytest.mark.anyio
@patch("app.services.registration_service.get_pending_queue_items")
@patch("app.services.registration_service.get_all_embeddings")
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_quota_exceeded_partial(
    mock_upsert_user, mock_get_processor, mock_get_all_embeddings, mock_get_pending_queue_items
):
    # Student S123 has 8 registered embeddings and 0 pending records (total = 8)
    mock_get_all_embeddings.return_value = [
        {
            "student_id": "S123",
            "embeddings": [[0.1] * 512] * 8
        }
    ]
    mock_get_pending_queue_items.return_value = []
    
    # Try to upload 3 images (8 + 3 = 11 > 10)
    mock_files = [MagicMock(spec=UploadFile) for _ in range(3)]
    for i, mock_file in enumerate(mock_files):
        mock_file.filename = f"pic_{i}.jpg"
        mock_file.read = AsyncMock(return_value=b"image_content")
        
    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", mock_files)
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Cannot register 3 photos. Already registered 8 photos. Remaining quota is 2 photos."


@pytest.mark.anyio
@patch("app.services.registration_service.get_pending_queue_items")
@patch("app.services.registration_service.get_all_embeddings")
@patch("app.services.registration_service.match_face_embedding")
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
async def test_register_images_duplicate_face_different_student(
    mock_upsert_user, mock_get_processor, mock_match_face, mock_get_all_embeddings, mock_get_pending_queue_items
):
    mock_get_all_embeddings.return_value = []
    mock_get_pending_queue_items.return_value = []
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    
    mock_processor = MagicMock()
    mock_processor.decode_image.return_value = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "results": {"face_detected": True, "single_face": True},
        "face": MagicMock()
    }
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor
    
    mock_match_face.return_value = {
        "student_id": "S456",
        "similarity": 0.85,
        "name": "Jane Doe",
        "user_id": 2
    }
    
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"image_content")
    
    with pytest.raises(HTTPException) as exc_info:
        await register_images("S123", "John Doe", [mock_file])
        
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "This face is already registered"


@pytest.mark.anyio
@patch("app.services.registration_service.get_pending_queue_items")
@patch("app.services.registration_service.get_all_embeddings")
@patch("app.services.registration_service.match_face_embedding")
@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
@patch("app.services.registration_service.upload_image")
@patch("app.services.registration_service.insert_queue_item")
async def test_register_images_duplicate_face_same_student(
    mock_insert_queue, mock_upload_image, mock_upsert_user, mock_get_processor, mock_match_face, mock_get_all_embeddings, mock_get_pending_queue_items
):
    mock_get_all_embeddings.return_value = []
    mock_get_pending_queue_items.return_value = []
    mock_upsert_user.return_value = {"id": 1, "student_id": "S123"}
    mock_upload_image.return_value = "http://storage.co/img.jpg"
    
    mock_processor = MagicMock()
    mock_processor.decode_image.return_value = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "results": {"face_detected": True, "single_face": True},
        "face": MagicMock()
    }
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor
    
    mock_match_face.return_value = {
        "student_id": "S123",
        "similarity": 0.95,
        "name": "John Doe",
        "user_id": 1
    }
    
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "pic.jpg"
    mock_file.read = AsyncMock(return_value=b"image_content")
    
    result = await register_images("S123", "John Doe", [mock_file])
    
    assert result["status"] == "pending"
    assert result["student_id"] == "S123"
    mock_insert_queue.assert_called_once()


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
    mock_update_status.assert_called_once_with(1, "completed", None)
    mock_save.assert_called_once()
    mock_invalidate.assert_called_once()
    assert result["message"] == "Training completed for batch"
    assert "S123" in result["processed_students"]


@patch("app.services.training_service.get_pending_queue_items")
@patch("app.services.training_service.get_face_processor")
@patch("app.services.training_service.update_queue_item_status")
@patch("app.services.training_service.get_all_embeddings")
@patch("app.services.training_service.save_all_embeddings")
@patch("app.services.training_service.invalidate_cache")
def test_process_pending_queue_batching(
    mock_invalidate, mock_save, mock_get_all, mock_update_status, mock_get_processor, mock_get_pending
):
    mock_get_pending.return_value = [
        {"id": 1, "student_id": "S123", "image_path": "/path/1.jpg"},
        {"id": 2, "student_id": "S123", "image_path": "/path/2.jpg"},
        {"id": 3, "student_id": "S456", "image_path": "/path/3.jpg"}
    ]
    mock_processor = MagicMock()
    mock_processor.decode_image_path.return_value = MagicMock()
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor
    mock_get_all.return_value = []

    result = process_pending_queue(limit=50)

    assert result["message"] == "Training completed for batch"
    assert "S123" in result["processed_students"]
    assert "S456" in result["processed_students"]
    assert mock_save.call_count == 2  # Once for S123, once for S456 (periodic saving)
    assert mock_update_status.call_count == 3



# ── Verification Service ─────────────────────────────────────────────

@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.insert_log")
def test_verify_face_match(mock_insert_log, mock_match, mock_decode, mock_get_processor):
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "results": {
            "face_detected": True,
            "single_face": True
        }
    }
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
    assert result["validation_checklist"]["database_match"] is True


@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.insert_log")
def test_verify_face_database_mismatch(mock_insert_log, mock_match, mock_decode, mock_get_processor):
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "results": {
            "face_detected": True,
            "single_face": True
        }
    }
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor

    mock_match.return_value = None

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    mock_decode.assert_called_once_with(b"image_bytes")
    mock_match.assert_called_once_with([0.1] * 512)
    mock_insert_log.assert_called_once_with(
        student_id=None, similarity_score=0.0, device_id="ESP-TEST", error_message="Employee data not found"
    )
    assert result["match"] is False
    assert result["student_id"] is None
    assert result["message"] == "Employee data not found"
    assert result["validation_checklist"]["database_match"] is False


@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.insert_log")
def test_verify_face_quality_failure(mock_insert_log, mock_decode, mock_get_processor):
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": False,
        "failed_step": 1,
        "error_message": "Please look at the camera",
        "results": {
            "face_detected": False,
            "single_face": False
        }
    }
    mock_get_processor.return_value = mock_processor

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    mock_insert_log.assert_called_once_with(
        student_id=None, similarity_score=0.0, device_id="ESP-TEST", error_message="Please look at the camera"
    )
    assert result["match"] is False
    assert result["student_id"] is None
    assert result["message"] == "Please look at the camera"
    assert result["validation_checklist"]["database_match"] is False


@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.get_latest_check_in_log")
@patch("app.services.verification_service.insert_log")
def test_verify_face_cooldown_active(mock_insert, mock_get_latest, mock_match, mock_decode, mock_get_processor):
    import datetime
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "results": {
            "face_detected": True,
            "single_face": True
        }
    }
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor
    mock_match.return_value = {"student_id": "S123", "similarity": 0.85, "user_id": 1}
    
    # Mock check-in 2 minutes ago (120 seconds ago)
    two_mins_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)
    mock_get_latest.return_value = {"timestamp": two_mins_ago}

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    assert result["match"] is True
    assert "already checked in" in result["message"]
    mock_insert.assert_not_called()  # Bypassed DB insert

@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.insert_log")
def test_verify_face_extraction_failure(mock_insert_log, mock_decode, mock_get_processor):
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": True,
        "results": {
            "face_detected": True,
            "single_face": True
        }
    }
    mock_processor.extract_face_embedding.return_value = None
    mock_get_processor.return_value = mock_processor

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    mock_insert_log.assert_called_once_with(
        student_id=None, similarity_score=0.0, device_id="ESP-TEST", error_message="Please look at the camera"
    )
    assert result["match"] is False
    assert result["student_id"] is None
    assert result["message"] == "Please look at the camera"
    assert result["validation_checklist"]["database_match"] is False


# ── New Tests for optimized training and timezone normalization ─────

@patch("app.services.training_service.get_pending_queue_items")
@patch("app.services.training_service.get_face_processor")
@patch("app.services.training_service.update_queue_item_status")
@patch("app.services.training_service.get_all_embeddings")
@patch("app.services.training_service.save_all_embeddings")
@patch("app.services.training_service.invalidate_cache")
def test_process_pending_queue_embedding_appending_and_capping(
    mock_invalidate, mock_save, mock_get_all, mock_update_status, mock_get_processor, mock_get_pending
):
    # Setup: S123 already has 19 embeddings in the database
    existing_embeddings = [[0.1] * 512] * 19
    mock_get_all.return_value = [
        {
            "user_id": "S123",
            "name": "S123",
            "student_id": "S123",
            "embeddings": existing_embeddings.copy()
        }
    ]
    
    # We will process 3 pending images for S123
    mock_get_pending.return_value = [
        {"id": 1, "student_id": "S123", "image_path": "/path/1.jpg"},
        {"id": 2, "student_id": "S123", "image_path": "/path/2.jpg"},
        {"id": 3, "student_id": "S123", "image_path": "/path/3.jpg"}
    ]
    
    mock_processor = MagicMock()
    mock_processor.decode_image_path.return_value = MagicMock()
    mock_processor.extract_face_embedding.side_effect = [
        {"embedding": [0.2] * 512},
        {"embedding": [0.3] * 512},
        {"embedding": [0.4] * 512}
    ]
    mock_get_processor.return_value = mock_processor

    # Track order of database status updates vs. pickle file saving to assert crash resilience
    call_order = []
    mock_save.side_effect = lambda *args: call_order.append("save_embeddings")
    mock_update_status.side_effect = lambda *args: call_order.append("update_status")

    result = process_pending_queue(limit=50)

    assert result["message"] == "Training completed for batch"
    assert "S123" in result["processed_students"]
    
    # Assert that save was called with the capped embeddings (19 + 3 = 22, capped at latest 20)
    mock_save.assert_called_once()
    saved_list = mock_save.call_args[0][0]
    assert len(saved_list) == 1
    assert saved_list[0]["student_id"] == "S123"
    assert len(saved_list[0]["embeddings"]) == 20
    # The last 3 embeddings should be the new ones we just added
    assert saved_list[0]["embeddings"][-1] == [0.4] * 512
    assert saved_list[0]["embeddings"][-2] == [0.3] * 512
    assert saved_list[0]["embeddings"][-3] == [0.2] * 512
    
    # Check calling order: saving embeddings should occur before updating database status
    assert "save_embeddings" in call_order
    assert "update_status" in call_order
    save_idx = call_order.index("save_embeddings")
    update_idx = call_order.index("update_status")
    assert save_idx < update_idx


@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.get_latest_check_in_log")
@patch("app.services.verification_service.insert_log")
def test_verify_face_timezone_aware_datetime(mock_insert, mock_get_latest, mock_match, mock_decode, mock_get_processor):
    import datetime
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor
    mock_match.return_value = {"student_id": "S123", "similarity": 0.85, "user_id": 1}
    
    # Mock check-in 2 minutes ago with UTC timezone
    tz_aware_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
    mock_get_latest.return_value = {"timestamp": tz_aware_time}

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    assert result["match"] is True
    assert "already checked in" in result["message"]
    mock_insert.assert_not_called()


@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.get_latest_check_in_log")
@patch("app.services.verification_service.insert_log")
def test_verify_face_timezone_aware_string(mock_insert, mock_get_latest, mock_match, mock_decode, mock_get_processor):
    import datetime
    mock_decode.return_value = MagicMock()
    mock_processor = MagicMock()
    mock_processor.extract_face_embedding.return_value = {"embedding": [0.1] * 512}
    mock_get_processor.return_value = mock_processor
    mock_match.return_value = {"student_id": "S123", "similarity": 0.85, "user_id": 1}
    
    # Mock check-in 2 minutes ago with ISO format ending in +00:00 or Z
    tz_aware_str = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)).isoformat()
    mock_get_latest.return_value = {"timestamp": tz_aware_str}

    result = verify_face(image_data=b"image_bytes", device_id="ESP-TEST")

    assert result["match"] is True
    assert "already checked in" in result["message"]
    mock_insert.assert_not_called()


@patch("app.services.registration_service.delete_student_from_db")
@patch("app.services.registration_service.get_all_embeddings")
@patch("app.services.registration_service.save_all_embeddings")
@patch("app.services.registration_service.invalidate_cache")
def test_delete_student_service_success(mock_invalidate, mock_save, mock_get_all, mock_db_delete):
    mock_db_delete.return_value = True
    mock_get_all.return_value = [
        {"student_id": "S123", "embeddings": []},
        {"student_id": "S456", "embeddings": []}
    ]
    
    from app.services.registration_service import delete_student
    result = delete_student("S123")
    
    assert result["student_id"] == "S123"
    assert "deleted successfully" in result["message"]
    mock_save.assert_called_once_with([{"student_id": "S456", "embeddings": []}])
    mock_invalidate.assert_called_once()


@patch("app.services.registration_service.delete_student_from_db")
def test_delete_student_service_failure(mock_db_delete):
    mock_db_delete.return_value = False
    
    from app.services.registration_service import delete_student
    with pytest.raises(HTTPException) as exc_info:
        delete_student("S123")
    
    assert exc_info.value.status_code == 500
    assert "Failed to delete student" in exc_info.value.detail


@patch("app.services.training_service.get_pending_queue_items")
@patch("app.services.training_service.get_face_processor")
@patch("app.services.training_service.update_queue_item_status")
@patch("app.services.training_service.get_all_embeddings")
@patch("app.services.training_service.save_all_embeddings")
@patch("app.services.training_service.invalidate_cache")
def test_process_pending_queue_validation_failure(
    mock_invalidate, mock_save, mock_get_all, mock_update_status, mock_get_processor, mock_get_pending
):
    mock_get_pending.return_value = [
        {"id": 1, "student_id": "S123", "image_path": "/path/1.jpg"}
    ]
    
    mock_processor = MagicMock()
    mock_processor.decode_image_path.return_value = MagicMock()
    mock_processor.validate_image_quality.return_value = {
        "passed": False,
        "failed_step": 1,
        "error_message": "Face not found, please retake",
        "results": {
            "face_detected": False,
            "single_face": False
        }
    }
    mock_get_processor.return_value = mock_processor
    mock_get_all.return_value = []

    result = process_pending_queue()

    mock_processor.decode_image_path.assert_called_once_with("/path/1.jpg")
    mock_processor.validate_image_quality.assert_called_once()
    mock_processor.extract_face_embedding.assert_not_called()
    mock_update_status.assert_called_once_with(1, "failed", "Face not found, please retake")
    mock_save.assert_not_called()
    mock_invalidate.assert_not_called()
    assert result["message"] == "Training completed for batch"
    assert "S123" not in result["processed_students"]



