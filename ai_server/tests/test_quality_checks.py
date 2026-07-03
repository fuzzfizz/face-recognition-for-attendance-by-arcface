import math
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from app.face_processor import get_face_processor
from app.utils.image_utils import calculate_blur_variance

class DummyFace:
    def __init__(self, bbox=None, kps=None, det_score=0.9):
        # Default bbox has size 150x150 (width = 250 - 100, height = 250 - 100)
        self.bbox = np.array(bbox if bbox is not None else [100, 100, 250, 250])
        # Default kps defines symmetric eyes and nose centered horizontally
        self.kps = np.array(kps if kps is not None else [
            [120, 150],  # left eye
            [180, 150],  # right eye
            [150, 180],  # nose
            [130, 220],  # left mouth corner
            [170, 220]   # right mouth corner
        ])
        self.det_score = det_score

def test_blur_variance_calculation():
    # Generate flat gray image (zero variance)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    assert calculate_blur_variance(img) == 0.0

def test_blur_variance_calculation_random():
    # Generate random noise image (non-zero variance)
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    assert calculate_blur_variance(img) > 0.0

def test_quality_checks_invalid_image():
    processor = get_face_processor()
    # None image
    res = processor.validate_image_quality(None)
    assert res["passed"] is False
    assert res["failed_step"] == 1
    assert "Invalid image" in res["error_message"]

    # Empty image
    empty_img = np.zeros((0, 0, 3), dtype=np.uint8)
    res = processor.validate_image_quality(empty_img)
    assert res["passed"] is False
    assert res["failed_step"] == 1
    assert "Invalid image" in res["error_message"]

def test_quality_checks_no_face():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    with patch.object(processor.app, "get", return_value=[]):
        res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 1
    assert "No face detected" in res["error_message"]

def test_quality_checks_multiple_faces():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace(), DummyFace()]
    with patch.object(processor.app, "get", return_value=faces):
        res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 2
    assert "Multiple faces detected" in res["error_message"]

def test_quality_checks_blur_failed():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace()]
    with patch.object(processor.app, "get", return_value=faces):
        # Force low blur variance
        with patch("app.face_processor.calculate_blur_variance", return_value=50.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 3
    assert "blurry" in res["error_message"]

def test_quality_checks_distance_failed():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Face too small/far: 100x100 box (width = 200 - 100, height = 200 - 100)
    faces = [DummyFace(bbox=[100, 100, 200, 200])]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 4
    assert "too far or too small" in res["error_message"]

def test_quality_checks_orientation_tilted():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Roll tilt: right eye is significantly higher than left eye
    # dy = 180 - 120 = 60, dx = 180 - 120 = 60
    # roll_angle = arctan(60/60) = 45 degrees (> 20)
    tilted_kps = [
        [120, 120],  # left eye
        [180, 180],  # right eye
        [150, 180],  # nose
        [130, 220],
        [170, 220]
    ]
    faces = [DummyFace(kps=tilted_kps)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 5
    assert "not straight (tilted" in res["error_message"]

def test_quality_checks_orientation_profile():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Profile view: nose is very close to left eye
    # left_dist = abs(121 - 120) = 1
    # right_dist = abs(180 - 121) = 59
    # yaw_ratio = 1 / 59 = 0.016 (< 0.5)
    profile_kps = [
        [120, 150],  # left eye
        [180, 150],  # right eye
        [121, 180],  # nose (shifted to left eye)
        [130, 220],
        [170, 220]
    ]
    faces = [DummyFace(kps=profile_kps)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 5
    assert "not straight (turned sideways" in res["error_message"]

def test_quality_checks_obstruction_failed():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace(det_score=0.5)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 6
    assert "Obstructions detected" in res["error_message"]

def test_quality_checks_all_passed():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace()]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is True
    assert res["failed_step"] is None
    assert res["error_message"] is None
    assert res["results"]["face_detected"] is True
    assert res["results"]["single_face"] is True
    assert res["results"]["blur_passed"] is True
    assert res["results"]["distance_passed"] is True
    assert res["results"]["orientation_passed"] is True
    assert res["results"]["obstruction_passed"] is True

def test_blur_variance_calculation_grayscale():
    # 2D single-channel grayscale image (zero variance)
    img_gray = np.zeros((100, 100), dtype=np.uint8)
    assert calculate_blur_variance(img_gray) == 0.0

    # 2D single-channel grayscale image (random noise)
    img_gray_random = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    assert calculate_blur_variance(img_gray_random) > 0.0

def test_quality_checks_orientation_pitch_down():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    pitch_down_kps = [
        [120, 150],  # left eye
        [180, 150],  # right eye
        [150, 200],  # nose (shifted down)
        [130, 220],  # left mouth corner
        [170, 220]   # right mouth corner
    ]
    faces = [DummyFace(kps=pitch_down_kps)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 5
    assert "tilted up/down: pitch" in res["error_message"]

def test_quality_checks_orientation_pitch_up():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    pitch_up_kps = [
        [120, 150],  # left eye
        [180, 150],  # right eye
        [150, 160],  # nose (shifted up)
        [130, 220],  # left mouth corner
        [170, 220]   # right mouth corner
    ]
    faces = [DummyFace(kps=pitch_up_kps)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 5
    assert "tilted up/down: pitch" in res["error_message"]

def test_quality_checks_orientation_invalid_vertical():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    invalid_vertical_kps = [
        [120, 150],  # left eye
        [180, 150],  # right eye
        [150, 180],  # nose
        [130, 140],  # left mouth corner (above eyes)
        [170, 140]   # right mouth corner (above eyes)
    ]
    faces = [DummyFace(kps=invalid_vertical_kps)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 5
    assert "invalid vertical features" in res["error_message"]
