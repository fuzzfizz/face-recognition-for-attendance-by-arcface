"""Tests for admin auth dependencies (Task 7)."""
import os
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch

from app.dependencies import require_admin

# Define a test app with a dependency-protected route
app = FastAPI()

@app.get("/protected")
def protected_route(admin=Depends(require_admin)):
    return {"status": "success"}

def test_admin_auth_success():
    with patch("app.dependencies.ADMIN_KEY", "secret-key"):
        client = TestClient(app)
        response = client.get("/protected", headers={"X-Admin-Key": "secret-key"})
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

def test_admin_auth_wrong_key():
    with patch("app.dependencies.ADMIN_KEY", "secret-key"):
        client = TestClient(app)
        response = client.get("/protected", headers={"X-Admin-Key": "wrong-key"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized"

def test_admin_auth_missing_header():
    with patch("app.dependencies.ADMIN_KEY", "secret-key"):
        client = TestClient(app)
        response = client.get("/protected")
        # FastAPI returns 422 Unprocessable Entity when required header is missing
        assert response.status_code == 422

def test_admin_auth_empty_env_key():
    with patch("app.dependencies.ADMIN_KEY", ""):
        client = TestClient(app)
        response = client.get("/protected", headers={"X-Admin-Key": "anything"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Unauthorized"
