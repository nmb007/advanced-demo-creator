"""Extract sample frames from scene/final videos for agent QA."""

from __future__ import annotations

import subprocess
from pathlib import Path

from demo_creator.video.render import find_ffmpeg


def extract_frames(
    video_path: Path,
    out_dir: Path,
    *,
    every_s: float = 2.0,
    prefix: str = "qa",
) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / f"{prefix}_%04d.png")
    ffmpeg = find_ffmpeg()
    # fps=1/every_s
    vf = f"fps=1/{every_s}"
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video_path), "-vf", vf, pattern],
        check=True,
        capture_output=True,
    )
    return [str(p) for p in sorted(out_dir.glob(f"{prefix}_*.png"))]
