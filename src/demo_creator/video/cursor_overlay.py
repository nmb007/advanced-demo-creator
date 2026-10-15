"""Composite a visible cursor onto rendered frames from the scene timeline."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def sample_cursor_css(timeline: dict[str, Any], t: float) -> tuple[float, float] | None:
    """
    Cursor position in CSS pixels at time t.

    Uses recorded cursor_paths. Instant paths (broken DOM cursor) still get a
    synthetic 350ms move into the target so the overlay animates.
    """
    paths = timeline.get("cursor_paths") or []
    if not paths:
        # Fall back to action target centers.
        steps = [
            s
            for s in timeline.get("steps", [])
            if s.get("box") and s.get("action") in ("click", "fill", "type", "select", "check", "hover")
        ]
        if not steps:
            return None
        paths = []
        for s in steps:
            box = s["box"]
            paths.append(
                {
                    "t_start": max(0.0, float(s["t_start"]) - 0.35),
                    "t_end": float(s["t_start"]),
                    "x": box["x"] + box["width"] / 2,
                    "y": box["y"] + box["height"] / 2,
                }
            )

    width = float(timeline.get("width") or 1920)
    height = float(timeline.get("height") or 1080)
    prev_x, prev_y = width / 2, height / 2

    for path in paths:
        x = float(path["x"])
        y = float(path["y"])
        t0 = float(path["t_start"])
        t1 = float(path["t_end"])
        # Guarantee a visible move even when recording stored a ~0ms path.
        if t1 - t0 < 0.12:
            t0 = max(0.0, t1 - 0.35)

        if t < t0:
            # Hold at previous point until this move starts.
            return prev_x, prev_y
        if t0 <= t <= t1:
            u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            e = _ease(u)
            return prev_x + (x - prev_x) * e, prev_y + (y - prev_y) * e
        prev_x, prev_y = x, y

    # After last path: keep holding on the last target.
    return prev_x, prev_y


def css_to_frame(
    x: float,
    y: float,
    *,
    cam_cx: float,
    cam_cy: float,
    zoom: float,
    out_w: int,
    out_h: int,
    css_w: int,
    css_h: int,
) -> tuple[int, int]:
    """Map CSS coordinates through the same crop used by ``_apply_zoom``."""
    zoom = max(1.0, min(2.0, zoom))
    crop_w = css_w / zoom
    crop_h = css_h / zoom
    x0 = cam_cx - crop_w / 2
    y0 = cam_cy - crop_h / 2
    # Mirror clamp from _apply_zoom
    x0 = max(0.0, min(x0, css_w - crop_w))
    y0 = max(0.0, min(y0, css_h - crop_h))
    ox = int((x - x0) / crop_w * out_w)
    oy = int((y - y0) / crop_h * out_h)
    return ox, oy


def _pointer_polygon(x: int, y: int, scale: float = 1.35) -> np.ndarray:
    """Arrow tip near (x,y), similar to the overlay SVG."""
    pts = np.array(
        [
            [0, 0],
            [1, 14],
            [5, 11],
            [9, 19],
            [12, 18],
            [8, 10],
            [14, 9],
        ],
        dtype=np.float32,
    )
    pts *= scale
    pts[:, 0] += x
    pts[:, 1] += y
    return pts.astype(np.int32)


def draw_cursor(
    frame: np.ndarray,
    x: int,
    y: int,
    *,
    press: bool = False,
) -> np.ndarray:
    """Draw a single high-contrast pointer onto a BGR frame."""
    h, w = frame.shape[:2]
    if x < -40 or y < -40 or x > w + 40 or y > h + 40:
        return frame
    out = frame
    # Brief soft click pulse behind the pointer (not a second arrow).
    if press:
        cv2.circle(out, (x + 4, y + 6), 22, (235, 120, 60), 2, lineType=cv2.LINE_AA)
    poly = _pointer_polygon(x, y)
    cv2.fillConvexPoly(out, poly, (17, 24, 39))  # near gray-900
    cv2.polylines(out, [poly], isClosed=True, color=(255, 255, 255), thickness=2, lineType=cv2.LINE_AA)
    return out


def click_active(timeline: dict[str, Any], t: float, window: float = 0.18) -> bool:
    for step in timeline.get("steps", []):
        if step.get("action") != "click":
            continue
        t0 = float(step.get("t_start") or 0)
        if abs(t - t0) <= window:
            return True
    return False


def overlay_cursor(
    frame: np.ndarray,
    timeline: dict[str, Any],
    t: float,
    *,
    cam_cx: float,
    cam_cy: float,
    zoom: float,
    out_w: int,
    out_h: int,
    css_w: int,
    css_h: int,
) -> np.ndarray:
    pos = sample_cursor_css(timeline, t)
    if pos is None:
        return frame
    ox, oy = css_to_frame(
        pos[0],
        pos[1],
        cam_cx=cam_cx,
        cam_cy=cam_cy,
        zoom=zoom,
        out_w=out_w,
        out_h=out_h,
        css_w=css_w,
        css_h=css_h,
    )
    return draw_cursor(frame, ox, oy, press=click_active(timeline, t))
