"""ffmpeg chapter metadata helpers."""

from __future__ import annotations

from pathlib import Path


def format_ffmetadata(chapters: list[tuple[str, float, float]]) -> str:
    """
    chapters: list of (title, start_sec, end_sec)
    """
    lines = [";FFMETADATA1"]
    for title, start, end in chapters:
        start_ms = int(start * 1000)
        end_ms = int(end * 1000)
        safe = title.replace("=", "-").replace(";", ",").replace("#", ".")
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={start_ms}")
        lines.append(f"END={end_ms}")
        lines.append(f"title={safe}")
    return "\n".join(lines) + "\n"


def write_ffmetadata(path: Path, chapters: list[tuple[str, float, float]]) -> Path:
    path.write_text(format_ffmetadata(chapters), encoding="utf-8")
    return path
