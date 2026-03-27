from __future__ import annotations

import logging
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


def _decode_uploaded_image(image_obj) -> Optional["np.ndarray"]:
    """Decode uploaded image bytes into an OpenCV BGR image."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    if not image_obj:
        return None

    try:
        if hasattr(image_obj, "open"):
            image_obj.open("rb")
        if hasattr(image_obj, "seek"):
            image_obj.seek(0)
        raw = image_obj.read()
        if hasattr(image_obj, "seek"):
            image_obj.seek(0)
        if not raw:
            return None
        buffer = np.frombuffer(raw, dtype=np.uint8)
        decoded = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        return decoded
    except Exception:
        logger.exception("Failed decoding image object for face verification.")
        return None


def _extract_single_face_encoding(image_obj):
    """Return one face encoding from an image object, or an error note."""
    try:
        import cv2
        import face_recognition
    except ImportError:
        return None, "Missing dependencies. Install face_recognition and opencv-python."

    bgr = _decode_uploaded_image(image_obj)
    if bgr is None:
        return None, "Invalid or unreadable image."

    # Normalize lighting to improve matching consistency across camera captures.
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    locations = face_recognition.face_locations(rgb, model="hog")
    if len(locations) == 0:
        return None, "No face detected."
    if len(locations) > 1:
        return None, "Multiple faces detected. Provide an image with one face."

    encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    if not encodings:
        return None, "Could not extract facial features."

    return encodings[0], ""


def verify_face_match(reference_image, probe_image, tolerance: float = 0.5) -> Tuple[bool, str]:
    """
    Verify that probe image matches a stored reference image.
    Returns `(is_match, note)`.
    """
    try:
        import face_recognition
    except ImportError:
        return False, "Face verification unavailable. Install face_recognition."

    if not reference_image or not probe_image:
        return False, "Missing reference or probe image."

    ref_encoding, ref_error = _extract_single_face_encoding(reference_image)
    if ref_encoding is None:
        return False, f"Reference image issue: {ref_error}"

    probe_encoding, probe_error = _extract_single_face_encoding(probe_image)
    if probe_encoding is None:
        return False, f"Probe image issue: {probe_error}"

    distance = float(face_recognition.face_distance([ref_encoding], probe_encoding)[0])
    is_match = distance <= tolerance
    if is_match:
        return True, f"Face verified (distance={distance:.3f}, tolerance={tolerance:.2f})."
    return False, f"Face mismatch (distance={distance:.3f}, tolerance={tolerance:.2f})."


def validate_face_probe_capture(probe_image, min_brightness: float = 40.0) -> Tuple[bool, str]:
    """
    Validate a pre-exam capture before starting an exam.
    Ensures the camera view is not too dark/covered and has exactly one visible face.
    """
    try:
        import cv2
        import face_recognition
    except ImportError:
        return False, "Face verification unavailable. Install face_recognition and opencv-python."

    bgr = _decode_uploaded_image(probe_image)
    if bgr is None:
        return False, "Invalid or unreadable image."

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    if brightness < min_brightness:
        return False, "Capture is too dark. Ensure the camera is not covered and your face is well lit."

    rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    locations = face_recognition.face_locations(rgb, model="hog")
    if len(locations) == 0:
        return False, "No face detected. Center your face in the camera and try again."
    if len(locations) > 1:
        return False, "Multiple faces detected. Only one face is allowed."

    return True, "Face capture validated."
