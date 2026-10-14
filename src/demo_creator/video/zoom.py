"""Build a camera zoom track from a scene timeline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class CameraKeyframe:
    t: float
    cx: float  # center x in CSS pixels
    cy: float
    zoom: float


def _ease_smooth(t: float) -> float:
    """Smoothstep / spring-ish ease."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def build_camera_track(
    timeline: dict[str, Any],
    *,
    width: int = 1920,
    height: int = 1080,
    zoom_in_lead: float = 0.4,
    hold: float = 0.25,
    zoom_out: float = 0.35,
    merge_time: float = 2.0,
    merge_dist: float = 300.0,
    max_pan_frac: float = 0.4,
) -> list[CameraKeyframe]:
    """
    Create keyframes: zoom in ~400ms before action, hold, zoom out.
    Nearby actions merge into one shot.
    """
    steps = [s for s in timeline.get("steps", []) if s.get("zoom") and s.get("box")]
    if not steps:
        return [CameraKeyframe(0.0, width / 2, height / 2, 1.0)]

    # Cluster nearby actions
    clusters: list[list[dict]] = []
    for step in steps:
        box = step["box"]
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2
        t = step["t_start"]
        if not clusters:
            clusters.append([step])
            continue
        prev = clusters[-1][-1]
        pb = prev["box"]
        pcx = pb["x"] + pb["width"] / 2
        pcy = pb["y"] + pb["height"] / 2
        if (t - prev["t_start"]) <= merge_time and math.hypot(cx - pcx, cy - pcy) <= merge_dist:
            clusters[-1].append(step)
        else:
            clusters.append([step])

    keyframes: list[CameraKeyframe] = [
        CameraKeyframe(0.0, width / 2, height / 2, 1.0)
    ]

    for cluster in clusters:
        boxes = [s["box"] for s in cluster]
        min_x = min(b["x"] for b in boxes)
        min_y = min(b["y"] for b in boxes)
        max_x = max(b["x"] + b["width"] for b in boxes)
        max_y = max(b["y"] + b["height"] for b in boxes)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        # Fit zoom so cluster fits with padding
        bw = max(max_x - min_x, 1)
        bh = max(max_y - min_y, 1)
        fit = min(width / (bw * 1.8), height / (bh * 1.8), 2.0)
        zoom = max(1.0, min(2.0, max(fit, float(cluster[0]["zoom"] or 1.5))))

        t_action = cluster[0]["t_start"]
        t_in = max(0.0, t_action - zoom_in_lead)
        t_hold_end = cluster[-1]["t_end"] + hold
        t_out_end = t_hold_end + zoom_out

        # Pan limit vs previous center
        prev = keyframes[-1]
        pan = math.hypot(cx - prev.cx, cy - prev.cy)
        if pan > max_pan_frac * width:
            # Zoom out toward midpoint while panning
            mid_x = (prev.cx + cx) / 2
            mid_y = (prev.cy + cy) / 2
            keyframes.append(CameraKeyframe(t_in, mid_x, mid_y, 1.0))

        keyframes.append(CameraKeyframe(t_in, cx, cy, 1.0))
        keyframes.append(CameraKeyframe(t_action, cx, cy, zoom))
        keyframes.append(CameraKeyframe(t_hold_end, cx, cy, zoom))
        keyframes.append(CameraKeyframe(t_out_end, cx, cy, 1.0))

    duration = float(timeline.get("duration") or 0)
    if keyframes[-1].t < duration:
        keyframes.append(CameraKeyframe(duration, width / 2, height / 2, 1.0))
    return keyframes


def sample_camera(track: list[CameraKeyframe], t: float) -> tuple[float, float, float]:
    """Interpolate camera (cx, cy, zoom) at time t."""
    if not track:
        return 960.0, 540.0, 1.0
    if t <= track[0].t:
        k = track[0]
        return k.cx, k.cy, k.zoom
    if t >= track[-1].t:
        k = track[-1]
        return k.cx, k.cy, k.zoom
    for i in range(len(track) - 1):
        a, b = track[i], track[i + 1]
        if a.t <= t <= b.t:
            span = b.t - a.t
            u = 0.0 if span <= 0 else (t - a.t) / span
            e = _ease_smooth(u)
            return (
                a.cx + (b.cx - a.cx) * e,
                a.cy + (b.cy - a.cy) * e,
                a.zoom + (b.zoom - a.zoom) * e,
            )
    k = track[-1]
    return k.cx, k.cy, k.zoom
