"""Free face counting (OpenCV YuNet, model in assets/models/) for flow-film quality checks.

A face counts when it is "clearly visible": detector score >= 0.8, at least 4 % of the frame width, and at least
35 % as wide as the biggest face in the frame. That ignores blurred background crowds and framed portraits, which
are much smaller than the people the shot is about (calibrated on the first MOS-001 keyframes).
Returns None when OpenCV is not installed, so callers can skip the check instead of failing.
"""
import subprocess
from pathlib import Path

from . import config

MODEL = config.ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
MIN_SCORE = 0.8
MIN_FRAC_OF_FRAME = 0.04
MIN_FRAC_OF_BIGGEST = 0.35


def _cv2():
    try:
        import cv2
        return cv2 if MODEL.exists() else None
    except ImportError:
        return None


def count_image(img) -> int | None:
    """img = path or a BGR numpy array."""
    cv2 = _cv2()
    if cv2 is None:
        return None
    if isinstance(img, (str, Path)):
        img = cv2.imread(str(img))
        if img is None:
            return None
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h), MIN_SCORE, 0.3, 5000)
    _, found = det.detect(img)
    if found is None:
        return 0
    widths = [float(f[2]) for f in found if float(f[14]) >= MIN_SCORE and float(f[2]) >= w * MIN_FRAC_OF_FRAME]
    if not widths:
        return 0
    big = max(widths)
    return sum(1 for x in widths if x >= big * MIN_FRAC_OF_BIGGEST)


def count_video(video: Path, times: list) -> list | None:
    """Face count at each time (seconds) of a video."""
    cv2 = _cv2()
    if cv2 is None:
        return None
    out = []
    for t in times:
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                            "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
        if r.returncode or not r.stdout:
            continue
        import numpy as np
        img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            out.append(count_image(img))
    return out


def typical(counts: list) -> int | None:
    """The middle value of a list of counts (robust to one bad frame)."""
    c = sorted(x for x in counts if x is not None)
    return c[len(c) // 2] if c else None
