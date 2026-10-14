"""Load optional .demo/profile.yaml from a target project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class TargetConfig(BaseModel):
    url: str
    auth: str | None = None
    unique_suffix: bool = False


class LoginConfig(BaseModel):
    url: str = "/login"
    fields: dict[str, str] = Field(default_factory=dict)
    submit: str | None = None


class HooksConfig(BaseModel):
    before_record: str | None = None
    after_record: str | None = None


class AppProfile(BaseModel):
    targets: dict[str, TargetConfig] = Field(default_factory=dict)
    hooks: HooksConfig = Field(default_factory=HooksConfig)
    selector_sources: list[str] = Field(default_factory=list)
    login: LoginConfig | None = None
    env_file: str | None = None


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) looking for .demo/profile.yaml or .git."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".demo" / "profile.yaml").is_file():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return cur


def profile_path(project_root: Path) -> Path:
    return project_root / ".demo" / "profile.yaml"


def load_profile(project_root: Path | None = None) -> AppProfile:
    root = project_root or find_project_root()
    path = profile_path(root)
    if not path.is_file():
        return AppProfile()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AppProfile.model_validate(data)


def resolve_target_url(plan_target: str, profile: AppProfile) -> tuple[str, TargetConfig | None]:
    """Return (base_url, target_config). plan_target may be a key or a full URL."""
    if plan_target.startswith("http://") or plan_target.startswith("https://"):
        return plan_target, None
    cfg = profile.targets.get(plan_target)
    if cfg:
        return cfg.url.rstrip("/"), cfg
    # Fall back: treat as relative path on first target, or localhost.
    if profile.targets:
        first = next(iter(profile.targets.values()))
        return first.url.rstrip("/"), first
    return "http://localhost:3000", None


def env_file_path(project_root: Path, profile: AppProfile) -> Path | None:
    if not profile.env_file:
        return None
    path = (project_root / profile.env_file).resolve()
    return path if path.is_file() else None


def profile_to_dict(profile: AppProfile) -> dict[str, Any]:
    return profile.model_dump()
