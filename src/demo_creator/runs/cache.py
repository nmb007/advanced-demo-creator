"""Content-hash caching for scene audio and video."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from demo_creator.paths import ensure_project_gitignore, project_runs_dir
from demo_creator.plan.schema import DemoPlan, Scene, VoiceSettings


def _hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def scene_audio_hash(scene: Scene, voice: VoiceSettings) -> str:
    payload = json.dumps(
        {"narration": scene.narration, "voice": voice.model_dump()},
        sort_keys=True,
    )
    return _hash(payload)


def scene_video_hash(
    scene: Scene,
    *,
    base_url: str,
    audio_duration: float,
    video_settings: dict,
) -> str:
    payload = json.dumps(
        {
            "id": scene.id,
            "start_url": scene.start_url,
            "steps": [s.model_dump() for s in scene.steps],
            "pace": scene.pace,
            "hold_after": scene.hold_after,
            "base_url": base_url,
            "audio_duration": round(audio_duration, 3),
            "video": video_settings,
        },
        sort_keys=True,
    )
    return _hash(payload)


class RunStore:
    def __init__(self, project_root: Path, run_id: str | None = None):
        self.project_root = project_root
        ensure_project_gitignore(project_root)
        self.runs_root = project_runs_dir(project_root)
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.run_dir = self.runs_root / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def scene_dir(self, scene_id: str) -> Path:
        path = self.run_dir / "scenes" / scene_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def audio_path(self, scene_id: str) -> Path:
        return self.scene_dir(scene_id) / "audio.wav"

    def video_path(self, scene_id: str) -> Path:
        return self.scene_dir(scene_id) / "scene.mp4"

    def timeline_path(self, scene_id: str) -> Path:
        return self.scene_dir(scene_id) / "timeline.json"

    def frames_dir(self, scene_id: str) -> Path:
        path = self.scene_dir(scene_id) / "frames"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def error_path(self, scene_id: str) -> Path:
        return self.scene_dir(scene_id) / "error.png"

    def meta_path(self) -> Path:
        return self.run_dir / "meta.json"

    def write_meta(self, data: dict[str, Any]) -> None:
        existing = {}
        if self.meta_path().is_file():
            existing = json.loads(self.meta_path().read_text(encoding="utf-8"))
        existing.update(data)
        self.meta_path().write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def read_meta(self) -> dict[str, Any]:
        if not self.meta_path().is_file():
            return {}
        return json.loads(self.meta_path().read_text(encoding="utf-8"))

    def scene_meta_path(self, scene_id: str) -> Path:
        return self.scene_dir(scene_id) / "meta.json"

    def write_scene_meta(self, scene_id: str, data: dict[str, Any]) -> None:
        path = self.scene_meta_path(scene_id)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_scene_meta(self, scene_id: str) -> dict[str, Any]:
        path = self.scene_meta_path(scene_id)
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def audio_cached(self, scene: Scene, voice: VoiceSettings) -> bool:
        path = self.audio_path(scene.id)
        meta = self.read_scene_meta(scene.id)
        return path.is_file() and meta.get("audio_hash") == scene_audio_hash(scene, voice)

    def video_cached(
        self,
        scene: Scene,
        *,
        base_url: str,
        audio_duration: float,
        video_settings: dict,
    ) -> bool:
        path = self.video_path(scene.id)
        meta = self.read_scene_meta(scene.id)
        expected = scene_video_hash(
            scene,
            base_url=base_url,
            audio_duration=audio_duration,
            video_settings=video_settings,
        )
        return path.is_file() and meta.get("video_hash") == expected

    @classmethod
    def latest(cls, project_root: Path) -> RunStore | None:
        root = project_runs_dir(project_root)
        if not root.is_dir():
            return None
        runs = sorted([p for p in root.iterdir() if p.is_dir()], reverse=True)
        if not runs:
            return None
        return cls(project_root, run_id=runs[0].name)

    @classmethod
    def open(cls, project_root: Path, run_id: str) -> RunStore:
        return cls(project_root, run_id=run_id)


def init_run_for_plan(project_root: Path, plan: DemoPlan, plan_path: Path) -> RunStore:
    store = RunStore(project_root)
    store.write_meta(
        {
            "plan_path": str(plan_path),
            "title": plan.title,
            "target": plan.target,
            "created": time.time(),
        }
    )
    return store
