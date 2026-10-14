"""Per-scene timeline of steps, cursor paths, and target boxes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Timeline:
    """Times are seconds relative to scene start (perf_counter offsets normalized on save)."""

    t0: float
    steps: list[dict[str, Any]] = field(default_factory=list)
    cursor_paths: list[dict[str, Any]] = field(default_factory=list)
    width: int = 1920
    height: int = 1080
    scale: int = 2

    def rel(self, t: float) -> float:
        return max(0.0, t - self.t0)

    def add_step(
        self,
        *,
        index: int,
        action: str,
        t_start: float,
        t_end: float,
        box: dict | None,
        zoom: float | None,
        masked: bool = False,
    ) -> None:
        self.steps.append(
            {
                "index": index,
                "action": action,
                "t_start": self.rel(t_start),
                "t_end": self.rel(t_end),
                "box": box,
                "zoom": zoom,
                "masked": masked,
            }
        )

    def add_cursor_path(
        self,
        t_start: float,
        t_end: float,
        x: float,
        y: float,
        box: dict | None,
    ) -> None:
        self.cursor_paths.append(
            {
                "t_start": self.rel(t_start),
                "t_end": self.rel(t_end),
                "x": x,
                "y": y,
                "box": box,
            }
        )

    def duration(self) -> float:
        ends = [s["t_end"] for s in self.steps] + [p["t_end"] for p in self.cursor_paths]
        return max(ends) if ends else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "scale": self.scale,
            "duration": self.duration(),
            "steps": self.steps,
            "cursor_paths": self.cursor_paths,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))
