"""
Image utility functions for decoding images from various sources.

Handles local file paths, URLs, raw bytes, and base64-encoded strings.
"""
import base64

import cv2
import numpy as np
import requests


def decode_image_from_source(source: str) -> np.ndarray | None:
    """
    Load an image from a local file path, URL, or database reference.

    If *source* starts with ``db://``, the image blob is loaded from
    the database and decoded in memory.
    If *source* starts with ``http://`` or ``https://``, the image is
    downloaded via :func:`requests.get` (timeout 10 s) and decoded in
    memory.  Otherwise it is read from the local filesystem with
    :func:`cv2.imread`.

    Returns an OpenCV BGR image (numpy array) or ``None`` on failure.
    """
    if source.startswith("db://"):
        from app.database import get_image_blob_by_ref
        blob_bytes = get_image_blob_by_ref(source)
        if blob_bytes:
            return decode_image_bytes(blob_bytes)
        return None

    if source.startswith("http://") or source.startswith("https://"):
        try:
            response = requests.get(source, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return None
        return decode_image_bytes(response.content)

    return cv2.imread(source)


def decode_image_bytes(data: bytes) -> np.ndarray | None:
    """
    Decode raw image bytes into an OpenCV BGR image.

    Returns a numpy array or ``None`` if the data cannot be decoded.
    """
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def decode_base64_image(b64: str) -> np.ndarray | None:
    """
    Decode a base64-encoded image string into an OpenCV BGR image.

    An optional ``data:image/...;base64,`` prefix is stripped
    automatically before decoding.

    Returns a numpy array or ``None`` on failure.
    """
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    try:
        img_data = base64.b64decode(b64)
    except Exception:
        return None
    return decode_image_bytes(img_data)


def calculate_blur_variance(cv_img: np.ndarray) -> float:
    """
    Calculate the Laplacian variance of the image to measure blurriness.
    """
    if cv_img is None or cv_img.size == 0:
        return 0.0
    if len(cv_img.shape) == 2:
        gray = cv_img
    else:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

