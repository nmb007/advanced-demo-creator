"""Resample screencast frames to 30fps with zoom crops; encode via ffmpeg."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from demo_creator.video.zoom import build_camera_track, sample_camera


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("ffmpeg not found; brew install ffmpeg") from exc


def _load_frame_index(frames_dir: Path) -> list[dict[str, Any]]:
    index_path = frames_dir / "index.json"
    if index_path.is_file():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        return data.get("frames", [])
    # Fallback: glob
    frames = []
    for i, path in enumerate(sorted(frames_dir.glob("frame_*.jpg"))):
        frames.append({"path": str(path), "t": i / 30.0, "index": i})
    return frames


def _frame_at(frames: list[dict], t: float) -> np.ndarray | None:
    if not frames:
        return None
    chosen = frames[0]
    for fr in frames:
        if fr["t"] <= t:
            chosen = fr
        else:
            break
    img = cv2.imread(chosen["path"])
    return img


def _apply_zoom(
    img: np.ndarray,
    cx: float,
    cy: float,
    zoom: float,
    *,
    out_w: int,
    out_h: int,
    css_w: int,
    css_h: int,
) -> np.ndarray:
    """Crop around (cx,cy) in CSS pixels and scale to out size. img is at device pixels."""
    h, w = img.shape[:2]
    scale_x = w / css_w
    scale_y = h / css_h
    zoom = max(1.0, min(2.0, zoom))
    crop_w = w / zoom
    crop_h = h / zoom
    center_x = cx * scale_x
    center_y = cy * scale_y
    x0 = int(center_x - crop_w / 2)
    y0 = int(center_y - crop_h / 2)
    x0 = max(0, min(x0, w - int(crop_w)))
    y0 = max(0, min(y0, h - int(crop_h)))
    x1 = min(w, x0 + int(crop_w))
    y1 = min(h, y0 + int(crop_h))
    crop = img[y0:y1, x0:x1]
    if crop.size == 0:
        return cv2.resize(img, (out_w, out_h))
    return cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)


def render_scene_video(
    frames_dir: Path,
    timeline_path: Path,
    out_path: Path,
    *,
    duration: float,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    css_w: int = 1920,
    css_h: int = 1080,
) -> Path:
    frames = _load_frame_index(frames_dir)
    timeline = json.loads(timeline_path.read_text(encoding="utf-8")) if timeline_path.is_file() else {}
    timeline.setdefault("duration", duration)
    track = build_camera_track(timeline, width=css_w, height=css_h)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-preset",
        "medium",
        str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    n_frames = max(1, int(math_ceil(duration * fps)))
    last_img = None
    try:
        for i in range(n_frames):
            t = i / fps
            img = _frame_at(frames, t)
            if img is None:
                img = last_img
            if img is None:
                img = np.zeros((height, width, 3), dtype=np.uint8)
            last_img = img
            cx, cy, zoom = sample_camera(track, t)
            framed = _apply_zoom(
                img, cx, cy, zoom, out_w=width, out_h=height, css_w=css_w, css_h=css_h
            )
            if framed.shape[0] != height or framed.shape[1] != width:
                framed = cv2.resize(framed, (width, height))
            proc.stdin.write(framed.tobytes())
    finally:
        proc.stdin.close()
        stderr = proc.stderr.read() if proc.stderr else b""
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg encode failed: {stderr[-2000:].decode(errors='ignore')}")
    return out_path


def math_ceil(x: float) -> int:
    import math

    return int(math.ceil(x))


def render_from_webm(
    webm_path: Path,
    timeline_path: Path,
    out_path: Path,
    *,
    duration: float,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """Fallback: remux/trim Playwright WebM to MP4 (no per-frame zoom)."""
    ffmpeg = find_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(webm_path),
        "-t",
        str(duration),
        "-vf",
        f"scale={width}:{height}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-an",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path
