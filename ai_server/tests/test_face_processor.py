"""Tests for FaceProcessor decoding delegation (Task 5)."""
import sys
from unittest.mock import MagicMock

# Mock insightface.app before importing FaceProcessor to avoid ModuleNotFoundError
sys.modules["insightface"] = MagicMock()
sys.modules["insightface.app"] = MagicMock()

import numpy as np
import pytest
from unittest.mock import patch

from app.face_processor import FaceProcessor

def test_decode_image():
    processor = FaceProcessor()
    fake_bytes = b"fake image bytes"
    fake_img = np.zeros((10, 10, 3), dtype=np.uint8)

    with patch("app.face_processor.decode_image_bytes", return_value=fake_img) as mock_decode:
        img = processor.decode_image(fake_bytes)
        mock_decode.assert_called_once_with(fake_bytes)
        assert img is fake_img

def test_decode_image_path():
    processor = FaceProcessor()
    fake_path = "/fake/path/to/image.jpg"
    fake_img = np.zeros((10, 10, 3), dtype=np.uint8)

    with patch("app.face_processor.decode_image_from_source", return_value=fake_img) as mock_decode:
        img = processor.decode_image_path(fake_path)
        mock_decode.assert_called_once_with(fake_path)
        assert img is fake_img
