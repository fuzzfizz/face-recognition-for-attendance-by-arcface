import os
import sys
import pickle
import pytest
from unittest.mock import MagicMock, patch

# Mock insightface so we do not need to compile/install it to run core tests!
mock_insightface = MagicMock()
sys.modules['insightface'] = mock_insightface
sys.modules['insightface.app'] = mock_insightface

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure we can import app modules from the ai_server directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, User, UserImage, CheckInLog, get_db
from app.config import EMBEDDINGS_PATH, SIMILARITY_THRESHOLD
from app.main import app
from app.matcher import match_face, save_embeddings, load_embeddings
from app.trainer import train_system

# --- SETUP IN-MEMORY DATABASE FOR TESTING ---
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh, clean in-memory database for each test.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """
    Overriding the database dependency in FastAPI with the in-memory test DB.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def temp_embeddings_path(tmp_path):
    """
    Mocks the EMBEDDINGS_PATH configuration to use a temporary directory during testing.
    """
    temp_file = tmp_path / "test_embeddings.pkl"
    with patch("app.matcher.EMBEDDINGS_PATH", temp_file), \
         patch("app.config.EMBEDDINGS_PATH", temp_file), \
         patch("app.trainer.save_embeddings", lambda data: _mock_save_embeddings(temp_file, data)):
        yield temp_file

def _mock_save_embeddings(path, data):
    with open(path, 'wb') as f:
        pickle.dump(data, f)

# --- UNIT TESTS: DATABASE MODELS ---

def test_create_user_and_image(db_session):
    """
    Test that users and user images can be created and the relationship is intact.
    """
    # Create User
    new_user = User(name="Test User")
    db_session.add(new_user)
    db_session.commit()
    
    assert new_user.id is not None
    assert new_user.name == "Test User"

    # Create User Image
    img = UserImage(user_id=new_user.id, image_base64="fake_base64_data_here")
    db_session.add(img)
    db_session.commit()

    assert img.id is not None
    assert img.user_id == new_user.id
    
    # Test relationship
    assert len(new_user.images) == 1
    assert new_user.images[0].image_base64 == "fake_base64_data_here"

# --- UNIT TESTS: MATCHER LOGIC ---

def test_matcher_no_file(temp_embeddings_path):
    """
    Test that matcher handles a non-existent embeddings file gracefully.
    """
    if temp_embeddings_path.exists():
        temp_embeddings_path.unlink()
        
    embeddings = load_embeddings()
    assert embeddings == []
    
    match = match_face([0.1] * 512)
    assert match is None

def test_matcher_matching_face(temp_embeddings_path):
    """
    Test the matching logic with dummy embeddings.
    """
    # Create two mock users
    # User 1: embedding of 1.0 at index 0 (rest 0)
    # User 2: embedding of 1.0 at index 1 (rest 0)
    user_1_emb = [0.0] * 512
    user_1_emb[0] = 1.0
    
    user_2_emb = [0.0] * 512
    user_2_emb[1] = 1.0

    mock_embeddings_data = [
        {"user_id": 1, "name": "Alice", "embeddings": [user_1_emb]},
        {"user_id": 2, "name": "Bob", "embeddings": [user_2_emb]}
    ]

    # Save to mock path
    with open(temp_embeddings_path, "wb") as f:
        pickle.dump(mock_embeddings_data, f)

    # Query matching Alice (Exact match)
    query_alice = [0.0] * 512
    query_alice[0] = 1.0
    
    match = match_face(query_alice)
    assert match is not None
    assert match["user_id"] == 1
    assert match["name"] == "Alice"
    assert match["similarity"] == pytest.approx(1.0)

    # Query matching Bob (High similarity)
    # Cosine Similarity of query with Bob should be high but not 1.0
    query_bob_approx = [0.0] * 512
    query_bob_approx[1] = 0.95
    query_bob_approx[2] = 0.312  # normalize-ish
    
    match = match_face(query_bob_approx)
    assert match is not None
    assert match["user_id"] == 2
    assert match["name"] == "Bob"
    assert match["similarity"] >= SIMILARITY_THRESHOLD

    # Query with no match (very low similarity to both)
    query_random = [0.0] * 512
    query_random[10] = 1.0 # different dimension
    
    match = match_face(query_random)
    assert match is None

# --- INTEGRATION TESTS: API ENDPOINTS ---

def test_api_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Face Recognition AI Server is running!"}

def test_api_create_and_list_users(client):
    # 1. Create a User
    response = client.post("/users", json={"name": "Jane Doe"})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["name"] == "Jane Doe"
    user_id = data["user_id"]

    # 2. List Users
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["user_id"] == user_id
    assert users[0]["name"] == "Jane Doe"

def test_api_upload_image(client):
    # Create user first
    create_res = client.post("/users", json={"name": "John Smith"})
    user_id = create_res.json()["user_id"]

    # Upload via Base64 JSON payload
    upload_res = client.post(
        f"/users/{user_id}/images", 
        json={"image_base64": "SGVsbG8gV29ybGQh"} # base64 of "Hello World!"
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["status"] == "success"
    assert upload_res.json()["user_id"] == user_id

@patch("app.trainer.get_face_processor")
def test_api_train_and_verify(mock_get_processor, client, temp_embeddings_path):
    # Setup mock FaceProcessor
    mock_processor = MagicMock()
    mock_get_processor.return_value = mock_processor
    
    # 1. Register User and Upload Image
    user_res = client.post("/users", json={"name": "Alex Mercer"})
    user_id = user_res.json()["user_id"]
    
    # Mock face embedding extraction to return a specific 512-d list
    mock_embedding = [0.0] * 512
    mock_embedding[0] = 1.0 # 1.0 at index 0
    mock_processor.extract_face_embedding.return_value = {
        "embedding": mock_embedding,
        "bbox": [10, 10, 100, 100],
        "kps": None
    }
    
    client.post(f"/users/{user_id}/images", json={"image_base64": "SGVsbG8gV29ybGQh"})

    # 2. Trigger training API
    with patch("app.trainer.get_face_processor", return_value=mock_processor):
        train_res = client.post("/train")
        assert train_res.status_code == 200
        assert train_res.json()["users_trained"] == 1
        assert train_res.json()["total_embeddings"] == 1

    # 3. Verify matching face
    with patch("app.main.get_face_processor", return_value=mock_processor):
        # Image base64 matches perfectly
        verify_res = client.post(
            "/verify",
            data={"image_base64": "SGVsbG8gV29ybGQh", "device_id": "esp32_device"}
        )
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "matched"
        assert verify_res.json()["user_id"] == user_id
        assert verify_res.json()["name"] == "Alex Mercer"

    # 4. Check check-in logs
    logs_res = client.get("/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 1
    assert logs[0]["user_id"] == user_id
    assert logs[0]["name"] == "Alex Mercer"
    assert logs[0]["device_id"] == "esp32_device"
