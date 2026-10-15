"""Pydantic models for demo storyboard plans."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ActionName = Literal[
    "goto",
    "click",
    "fill",
    "type",
    "select",
    "check",
    "hover",
    "press",
    "scroll",
    "wait_for",
    "wait",
    "highlight",
]

PaceMode = Literal["spread", "front", "back"]
ZoomValue = float | Literal["auto", "off"]


class Target(BaseModel):
    """How to find an element on the page."""

    role: str | None = None
    name: str | None = None
    label: str | None = None
    text: str | None = None
    testid: str | None = None
    css: str | None = None
    frame: str | None = None  # CSS selector or name of an iframe

    @model_validator(mode="after")
    def _at_least_one(self) -> Target:
        keys = (self.role, self.label, self.text, self.testid, self.css)
        if not any(keys):
            raise ValueError(
                "Target needs at least one of: role, label, text, testid, css"
            )
        return self


class Step(BaseModel):
    action: ActionName
    target: Target | None = None
    value: str | None = None
    url: str | None = None
    keys: str | None = None  # for press
    ms: int | None = None  # for wait
    zoom: ZoomValue = "auto"
    mask: bool = False
    hold_ms: int | None = None

    @model_validator(mode="after")
    def _validate_action(self) -> Step:
        if self.action == "goto" and not self.url:
            raise ValueError("goto requires url")
        if self.action in ("click", "fill", "type", "select", "check", "hover", "highlight", "wait_for"):
            if self.target is None:
                raise ValueError(f"{self.action} requires target")
        if self.action in ("fill", "type", "select") and self.value is None:
            raise ValueError(f"{self.action} requires value")
        if self.action == "press" and not self.keys:
            raise ValueError("press requires keys")
        if self.action == "wait" and self.ms is None:
            raise ValueError("wait requires ms")
        return self

    def effective_zoom(self) -> float | None:
        """Return zoom factor, or None for no zoom."""
        if self.zoom == "off":
            return None
        if self.zoom == "auto":
            if self.action in ("click", "fill", "type", "select", "check"):
                return 1.5
            return None
        return float(self.zoom)


class VoiceSettings(BaseModel):
    engine: Literal["kokoro", "say"] = "kokoro"
    name: str = "am_michael"
    speed: float = 1.0


class VideoSettings(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: int = 30
    scale: int = 2  # device pixel ratio for capture


class Scene(BaseModel):
    id: str
    narration: str = ""
    start_url: str | None = None
    steps: list[Step] = Field(default_factory=list)
    pace: PaceMode = "spread"
    hold_after: float = 0.5  # seconds paused after actions / audio
    # None = inherit plan/target auth; "none"/"" = force logged-out browser
    auth: str | None = None

    @field_validator("id")
    @classmethod
    def _slug_id(cls, v: str) -> str:
        if not v or "/" in v or "\\" in v:
            raise ValueError("scene id must be a simple slug")
        return v


class Chapter(BaseModel):
    title: str
    scenes: list[Scene] = Field(default_factory=list)


class DemoPlan(BaseModel):
    title: str
    target: str = "local"  # profile key or absolute URL
    auth: str | None = None
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    chapters: list[Chapter] = Field(default_factory=list)
    lead_in_ms: int = 300

    def all_scenes(self) -> list[Scene]:
        scenes: list[Scene] = []
        for chapter in self.chapters:
            scenes.extend(chapter.scenes)
        return scenes

    def scene_by_id(self, scene_id: str) -> Scene | None:
        for scene in self.all_scenes():
            if scene.id == scene_id:
                return scene
        return None

    def estimate_seconds(self, words_per_minute: float = 150.0) -> dict[str, Any]:
        """Rough length from narration word counts."""
        chapters_out = []
        total = 0.0
        for chapter in self.chapters:
            ch_secs = 0.0
            scenes_out = []
            for scene in chapter.scenes:
                words = len(scene.narration.split()) if scene.narration else 0
                secs = max(words / words_per_minute * 60.0, 1.5) + scene.hold_after
                secs += self.lead_in_ms / 1000.0
                ch_secs += secs
                scenes_out.append({"id": scene.id, "seconds": round(secs, 1), "words": words})
            total += ch_secs
            chapters_out.append(
                {
                    "title": chapter.title,
                    "seconds": round(ch_secs, 1),
                    "scenes": scenes_out,
                }
            )
        return {
            "title": self.title,
            "total_seconds": round(total, 1),
            "total_minutes": round(total / 60.0, 2),
            "chapters": chapters_out,
            "scene_count": len(self.all_scenes()),
            "chapter_count": len(self.chapters),
        }
