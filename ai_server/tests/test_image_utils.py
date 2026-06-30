"""Tests for ai_server.app.utils.image_utils."""
import base64
import os
import tempfile

import cv2
import numpy as np
import pytest

from app.utils.image_utils import (
    decode_base64_image,
    decode_image_bytes,
    decode_image_from_source,
)


def _make_tiny_png_bytes() -> bytes:
    """Create a minimal 2x2 red PNG image and return its bytes."""
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    img[:, :] = (0, 0, 255)  # BGR red
    success, buf = cv2.imencode(".png", img)
    assert success
    return buf.tobytes()


def _make_tiny_jpeg_bytes() -> bytes:
    """Create a minimal 2x2 blue JPEG image and return its bytes."""
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    img[:, :] = (255, 0, 0)  # BGR blue
    success, buf = cv2.imencode(".jpg", img)
    assert success
    return buf.tobytes()


# ── decode_image_bytes ──────────────────────────────────────────────


class TestDecodeImageBytes:
    def test_valid_jpeg(self):
        raw = _make_tiny_jpeg_bytes()
        img = decode_image_bytes(raw)
        assert img is not None
        assert isinstance(img, np.ndarray)
        assert img.shape[0] == 2 and img.shape[1] == 2

    def test_valid_png(self):
        raw = _make_tiny_png_bytes()
        img = decode_image_bytes(raw)
        assert img is not None
        assert img.shape == (2, 2, 3)

    def test_invalid_bytes_returns_none(self):
        img = decode_image_bytes(b"not-an-image")
        assert img is None


# ── decode_image_from_source (local path) ───────────────────────────


class TestDecodeImageFromSourceLocal:
    def test_valid_local_png(self, tmp_path):
        png_bytes = _make_tiny_png_bytes()
        file_path = str(tmp_path / "test.png")
        with open(file_path, "wb") as f:
            f.write(png_bytes)

        img = decode_image_from_source(file_path)
        assert img is not None
        assert img.shape == (2, 2, 3)

    def test_nonexistent_path_returns_none(self):
        img = decode_image_from_source("C:\\nonexistent\\fake_image.png")
        assert img is None


# ── decode_base64_image ─────────────────────────────────────────────


class TestDecodeBase64Image:
    def test_plain_base64(self):
        raw = _make_tiny_jpeg_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        img = decode_base64_image(b64)
        assert img is not None
        assert isinstance(img, np.ndarray)

    def test_data_uri_prefix(self):
        raw = _make_tiny_png_bytes()
        b64 = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        img = decode_base64_image(b64)
        assert img is not None
        assert img.shape == (2, 2, 3)

    def test_invalid_base64_returns_none(self):
        img = decode_base64_image("!!!not-valid-base64!!!")
        assert img is None
