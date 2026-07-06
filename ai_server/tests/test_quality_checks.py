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
    assert "Please look at the camera" in res["error_message"]

    # Empty image
    empty_img = np.zeros((0, 0, 3), dtype=np.uint8)
    res = processor.validate_image_quality(empty_img)
    assert res["passed"] is False
    assert res["failed_step"] == 1
    assert "Please look at the camera" in res["error_message"]

def test_quality_checks_no_face():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    with patch.object(processor.app, "get", return_value=[]):
        res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 1
    assert "Please look at the camera" in res["error_message"]

def test_quality_checks_multiple_faces():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace(), DummyFace()]
    with patch.object(processor.app, "get", return_value=faces):
        res = processor.validate_image_quality(blank_img)
    assert res["passed"] is False
    assert res["failed_step"] == 2
    assert "One person at a time" in res["error_message"]

def test_quality_checks_blur_ignored():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace()]
    with patch.object(processor.app, "get", return_value=faces):
        # Even with low blur variance, the check should pass
        with patch("app.face_processor.calculate_blur_variance", return_value=50.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is True
    assert res["failed_step"] is None

def test_quality_checks_distance_ignored():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Face too small/far: 100x100 box
    faces = [DummyFace(bbox=[100, 100, 200, 200])]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is True
    assert res["failed_step"] is None

def test_quality_checks_orientation_tilted_ignored():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
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
    assert res["passed"] is True
    assert res["failed_step"] is None

def test_quality_checks_orientation_profile_ignored():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
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
    assert res["passed"] is True
    assert res["failed_step"] is None

def test_quality_checks_obstruction_ignored():
    processor = get_face_processor()
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    faces = [DummyFace(det_score=0.5)]
    with patch.object(processor.app, "get", return_value=faces):
        with patch("app.face_processor.calculate_blur_variance", return_value=150.0):
            res = processor.validate_image_quality(blank_img)
    assert res["passed"] is True
    assert res["failed_step"] is None

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
    assert "blur_passed" not in res["results"]
    assert "distance_passed" not in res["results"]
    assert "orientation_passed" not in res["results"]
    assert "obstruction_passed" not in res["results"]

def test_blur_variance_calculation_grayscale():
    # 2D single-channel grayscale image (zero variance)
    img_gray = np.zeros((100, 100), dtype=np.uint8)
    assert calculate_blur_variance(img_gray) == 0.0

    # 2D single-channel grayscale image (random noise)
    img_gray_random = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
    assert calculate_blur_variance(img_gray_random) > 0.0

def test_quality_checks_orientation_pitch_down_ignored():
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
    assert res["passed"] is True
    assert res["failed_step"] is None

def test_quality_checks_orientation_pitch_up_ignored():
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
    assert res["passed"] is True
    assert res["failed_step"] is None

def test_quality_checks_orientation_invalid_vertical_ignored():
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
    assert res["passed"] is True
    assert res["failed_step"] is None
