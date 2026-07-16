import pytest
from unittest.mock import MagicMock, patch
import datetime
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.services.verification_service import verify_face

client = TestClient(app)

@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.match_face_embedding")
@patch("app.services.verification_service.insert_log")
def test_verify_face_with_short_year_timestamp(
    mock_insert_log, mock_match, mock_decode, mock_get_processor
):
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

    # Test the 2-digit year format sent by ESP32: "26-07-16T01:58:25.229103"
    short_ts_str = "26-07-16T01:58:25.229103"
    result = verify_face(
        image_data=b"image_bytes",
        device_id="ESP32-S3-01",
        timestamp=short_ts_str
    )

    # The expected parsed datetime object should be 2026-07-16 01:58:25.229103
    expected_dt = datetime.datetime(2026, 7, 16, 1, 58, 25, 229103)
    
    mock_insert_log.assert_called_once_with(
        student_id="S123",
        similarity_score=0.85,
        device_id="ESP32-S3-01",
        user_id=1,
        timestamp=expected_dt
    )
    assert result["match"] is True
    assert result["timestamp"] == expected_dt.isoformat()


@patch("app.services.verification_service.verify_face")
def test_verify_endpoint_query_params(mock_verify):
    mock_verify.return_value = {
        "match": True, 
        "student_id": "S123", 
        "similarity_score": 0.85,
        "timestamp": "2026-07-16T01:58:25.229103",
        "validation_checklist": {
            "face_detected": True,
            "single_face": True,
            "database_match": True
        }
    }
    
    # 1. Test sending timestamp in query param for new endpoint
    response = client.post(
        "/verify/face_recognition/ESP32-S3-01?timestamp=26-07-16T01:58:25.229103",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 200
    mock_verify.assert_called_with(
        image_data=b"fakebytes",
        image_base64=None,
        device_id="ESP32-S3-01",
        timestamp="26-07-16T01:58:25.229103"
    )

    mock_verify.reset_mock()

    # 2. Test sending timestamp and device_id in query param for legacy endpoint
    response = client.post(
        "/verify?device_id=ESP32-LEGACY&timestamp=26-07-16T01:58:25.229103",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 200
    mock_verify.assert_called_with(
        image_data=b"fakebytes",
        image_base64=None,
        device_id="ESP32-LEGACY",
        timestamp="26-07-16T01:58:25.229103"
    )
