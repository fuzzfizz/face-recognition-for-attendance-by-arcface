"""Integration tests for all API routers (Task 9)."""
import sys
from unittest.mock import MagicMock

# Mock insightface.app before importing anything else
sys.modules["insightface"] = MagicMock()
sys.modules["insightface.app"] = MagicMock()

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch

from app.routers import registration, training, verification, logs
from app.routers.v1 import users as v1_users

# Create a test FastAPI app and include all routers
app = FastAPI()
app.include_router(registration.router)
app.include_router(training.router)
app.include_router(verification.router)
app.include_router(logs.router)
app.include_router(v1_users.router, prefix="/v1")

client = TestClient(app)


# ── /register ────────────────────────────────────────────────────────

@patch("app.services.registration_service.register_images")
def test_register_route(mock_register):
    mock_register.return_value = {"message": "queued", "student_id": "S001", "status": "pending"}
    
    response = client.post(
        "/register",
        data={"student_id": "S001"},
        files={"files": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    mock_register.assert_called_once()


# ── /register/status/{student_id} ────────────────────────────────────

@patch("app.services.registration_service.get_registration_status")
def test_status_route(mock_status):
    mock_status.return_value = {"student_id": "S001", "status": "completed", "message": "Face saved"}
    
    response = client.get("/register/status/S001")
    
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    mock_status.assert_called_once_with("S001")


# ── DELETE /register/student/{student_id} ────────────────────────────

@patch("app.services.registration_service.delete_student")
@patch("app.dependencies.ADMIN_KEY", "secret")
def test_delete_student_unauthorized(mock_delete):
    response = client.delete("/register/student/S001")
    assert response.status_code == 401  # missing header

    response = client.delete("/register/student/S001", headers={"X-Admin-Key": "wrong"})
    assert response.status_code == 401  # unauthorized
    mock_delete.assert_not_called()


@patch("app.services.registration_service.delete_student")
@patch("app.dependencies.ADMIN_KEY", "secret")
def test_delete_student_authorized(mock_delete):
    mock_delete.return_value = {
        "message": "Student registration data deleted successfully",
        "student_id": "S001"
    }

    response = client.delete("/register/student/S001", headers={"X-Admin-Key": "secret"})
    assert response.status_code == 200
    assert response.json()["student_id"] == "S001"
    mock_delete.assert_called_once_with("S001")



# ── /train-now ───────────────────────────────────────────────────────

@patch("app.services.training_service.process_pending_queue")
@patch("app.dependencies.ADMIN_KEY", "secret")
def test_train_now_unauthorized(mock_process):
    response = client.post("/train-now")
    assert response.status_code == 401  # missing header

    response = client.post("/train-now", headers={"X-Admin-Key": "wrong"})
    assert response.status_code == 401  # unauthorized
    mock_process.assert_not_called()

@patch("app.services.training_service.process_pending_queue")
@patch("app.dependencies.ADMIN_KEY", "secret")
def test_train_now_authorized(mock_process):
    mock_process.return_value = {"message": "completed", "processed_students": [], "total_pending": 0}
    
    response = client.post("/train-now", headers={"X-Admin-Key": "secret"})
    assert response.status_code == 200
    assert response.json()["message"] == "completed"
    mock_process.assert_called_once_with(limit=50)

@patch("app.services.training_service.process_pending_queue")
@patch("app.dependencies.ADMIN_KEY", "secret")
def test_train_now_with_limit(mock_process):
    mock_process.return_value = {"message": "completed", "processed_students": [], "total_pending": 0}
    
    response = client.post("/train-now?limit=10", headers={"X-Admin-Key": "secret"})
    assert response.status_code == 200
    assert response.json()["message"] == "completed"
    mock_process.assert_called_once_with(limit=10)

@patch("app.services.training_service.process_pending_queue")
@patch("app.dependencies.ADMIN_KEY", "secret")
def test_v1_train_authorized(mock_process):
    mock_process.return_value = {"message": "completed", "processed_students": [], "total_pending": 0}
    
    response = client.post("/v1/train?limit=5", headers={"X-Admin-Key": "secret"})
    assert response.status_code == 200
    assert response.json()["message"] == "completed"
    mock_process.assert_called_once_with(limit=5)



# ── /verify ──────────────────────────────────────────────────────────

@patch("app.services.verification_service.verify_face")
def test_verify_route(mock_verify):
    mock_verify.return_value = {
        "match": True,
        "student_id": "S001",
        "similarity_score": 0.85,
        "timestamp": "2026-06-29T18:00:00",
        "validation_checklist": {
            "face_detected": True,
            "single_face": True,
            "database_match": True
        }
    }
    
    response = client.post(
        "/verify/face_recognition/ESP-01",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["match"] is True
    assert res_json["validation_checklist"]["database_match"] is True
    mock_verify.assert_called_once()


@patch("app.services.verification_service.verify_face")
def test_verify_legacy_route(mock_verify):
    mock_verify.return_value = {
        "match": True,
        "student_id": "S001",
        "similarity_score": 0.85,
        "timestamp": "2026-07-15T15:20:00",
        "validation_checklist": {
            "face_detected": True,
            "single_face": True,
            "database_match": True
        }
    }

    # 1. Test legacy route with custom device_id and custom timestamp
    response = client.post(
        "/verify",
        data={"device_id": "ESP32-LEGACY", "timestamp": "2026-07-15T15:20:00"},
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["match"] is True
    assert res_json["timestamp"] == "2026-07-15T15:20:00"
    mock_verify.assert_called_with(
        image_data=b"fakebytes",
        image_base64=None,
        device_id="ESP32-LEGACY",
        timestamp="2026-07-15T15:20:00"
    )

    mock_verify.reset_mock()

    # 2. Test legacy route with default device_id and no timestamp
    response_default = client.post(
        "/verify",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response_default.status_code == 200
    mock_verify.assert_called_with(
        image_data=b"fakebytes",
        image_base64=None,
        device_id="ESP32-S3-01",
        timestamp=None
    )


def test_verify_route_device_id_validation():
    # Test path parameter validation on device_id (pattern check)
    response_invalid_pattern = client.post(
        "/verify/face_recognition/ESP@01",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response_invalid_pattern.status_code == 422

    # Test path parameter validation on device_id (max_length check)
    response_too_long = client.post(
        f"/verify/face_recognition/{'a' * 51}",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response_too_long.status_code == 422



# ── /logs ────────────────────────────────────────────────────────────

@patch("app.routers.logs.get_logs")
def test_logs_route(mock_get_logs):
    mock_get_logs.return_value = []
    
    response = client.get("/logs?limit=10")
    
    assert response.status_code == 200
    assert response.json() == []
    mock_get_logs.assert_called_once_with(10)


# ── v1 Legacy Endpoints ──────────────────────────────────────────────

@patch("app.routers.v1.users.upsert_user")
def test_v1_users_create(mock_upsert):
    mock_upsert.return_value = {"id": 1, "student_id": "S123"}
    
    response = client.post("/v1/users", json={"name": "Alice"})
    
    assert response.status_code == 201
    assert response.json()["status"] == "success"
    mock_upsert.assert_called_once_with("Alice")

@patch("app.routers.v1.users.get_all_embeddings")
def test_v1_users_list(mock_get_all):
    mock_get_all.return_value = [{"user_id": 1, "student_id": "S123", "embeddings": [[0.1]*512]}]
    
    response = client.get("/v1/users")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["student_id"] == "S123"

@patch("app.routers.v1.users.upload_image")
def test_v1_user_image_upload(mock_upload):
    mock_upload.return_value = 1
    
    response = client.post(
        "/v1/users/123/images",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    
    assert response.status_code == 201
    assert response.json()["status"] == "success"
    mock_upload.assert_called_once()


@patch("app.dependencies.ADMIN_KEY", "secret")
def test_student_id_validation_invalid():
    # Test invalid student_id pattern (e.g. with spaces, slashes, special characters)
    # 1. /register
    response = client.post(
        "/register",
        data={"student_id": "invalid/student_id"},
        files={"files": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 400
    assert "Invalid student_id format" in response.json()["detail"]

    # 2. /register/status/{student_id}
    response = client.get("/register/status/invalid id")
    assert response.status_code == 400
    assert "Invalid student_id format" in response.json()["detail"]

    # 3. DELETE /register/student/{student_id}
    response = client.delete("/register/student/invalid&id", headers={"X-Admin-Key": "secret"})
    assert response.status_code == 400
    assert "Invalid student_id format" in response.json()["detail"]


@patch("app.services.verification_service.decode_image_bytes")
@patch("app.services.verification_service.get_face_processor")
@patch("app.services.verification_service.insert_log")
def test_verify_route_validation_failure(mock_insert_log, mock_get_processor, mock_decode):
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

    response = client.post(
        "/verify/face_recognition/ESP-TEST-01",
        files={"file": ("file.jpg", b"fakebytes", "image/jpeg")}
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["match"] is False
    assert res_json["student_id"] is None
    assert res_json["similarity_score"] == 0.0
    assert "Please look at the camera" in res_json["message"]
    assert res_json["validation_checklist"]["face_detected"] is False
    assert res_json["validation_checklist"]["database_match"] is False
    
    mock_insert_log.assert_called_once_with(
        student_id=None,
        similarity_score=0.0,
        device_id="ESP-TEST-01",
        error_message="Please look at the camera"
    )


@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
def test_register_route_validation_failure(mock_upsert, mock_get_processor):
    mock_upsert.return_value = {"id": 1, "student_id": "S001"}
    
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

    response = client.post(
        "/register",
        data={"student_id": "S001"},
        files={"files": ("file.jpg", b"fakebytes", "image/jpeg")}
    )

    assert response.status_code == 400
    res_json = response.json()
    assert "Some photos failed face verification" in res_json["detail"]["message"]
    assert res_json["detail"]["results"][0]["error"] == "Face not found, please retake"


@patch("app.face_processor.get_face_processor")
@patch("app.services.registration_service.upsert_user")
def test_register_route_empty_file(mock_upsert, mock_get_processor):
    mock_upsert.return_value = {"id": 1, "student_id": "S001"}
    
    mock_processor = MagicMock()
    mock_get_processor.return_value = mock_processor

    response = client.post(
        "/register",
        data={"student_id": "S001"},
        files={"files": ("file.jpg", b"", "image/jpeg")}
    )

    assert response.status_code == 400
    res_json = response.json()
    assert "Some photos failed face verification" in res_json["detail"]["message"]
    assert res_json["detail"]["results"][0]["error"] == "Empty upload file"
    assert res_json["detail"]["results"][0]["validation_checklist"]["database_match"] is None


@patch("app.services.registration_service.register_images")
def test_register_route_quota_full(mock_register):
    from fastapi import HTTPException
    mock_register.side_effect = HTTPException(
        status_code=400,
        detail={
            "message": "Already registered 10 photos (Quota full)",
            "results": []
        }
    )
    response = client.post(
        "/register",
        data={"student_id": "S001"},
        files={"files": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "message": "Already registered 10 photos (Quota full)",
        "results": []
    }


@patch("app.services.registration_service.register_images")
def test_register_route_quota_partial(mock_register):
    from fastapi import HTTPException
    mock_register.side_effect = HTTPException(
        status_code=400,
        detail={
            "message": "Cannot register 3 photos. Already registered 8 photos. Remaining quota is 2 photos.",
            "results": []
        }
    )
    response = client.post(
        "/register",
        data={"student_id": "S001"},
        files={"files": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "message": "Cannot register 3 photos. Already registered 8 photos. Remaining quota is 2 photos.",
        "results": []
    }


@patch("app.services.registration_service.register_images")
def test_register_route_duplicate_face(mock_register):
    from fastapi import HTTPException
    mock_register.side_effect = HTTPException(
        status_code=400,
        detail={
            "message": "This face is already registered",
            "results": []
        }
    )
    response = client.post(
        "/register",
        data={"student_id": "S001"},
        files={"files": ("file.jpg", b"fakebytes", "image/jpeg")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "message": "This face is already registered",
        "results": []
    }

