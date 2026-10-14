"""Load and expand demo plan YAML/JSON files."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from demo_creator.plan.schema import DemoPlan

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _unique_token() -> str:
    return datetime.now().strftime("%m%d-%H%M")


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        values[key] = val
    return values


def expand_string(value: str, env: dict[str, str], unique: str) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "UNIQUE":
            return unique
        if name in env:
            return env[name]
        if name in os.environ:
            return os.environ[name]
        # Leave unresolved so validation / runtime can surface it.
        return match.group(0)

    return _ENV_PATTERN.sub(repl, value)


def expand_obj(obj: Any, env: dict[str, str], unique: str) -> Any:
    if isinstance(obj, str):
        return expand_string(obj, env, unique)
    if isinstance(obj, list):
        return [expand_obj(item, env, unique) for item in obj]
    if isinstance(obj, dict):
        return {k: expand_obj(v, env, unique) for k, v in obj.items()}
    return obj


def load_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Plan must be a mapping: {path}")
    return data


def load_plan(
    path: Path | str,
    *,
    env: dict[str, str] | None = None,
    env_file: Path | None = None,
    expand: bool = True,
    unique: str | None = None,
) -> DemoPlan:
    path = Path(path)
    raw = load_raw(path)
    merged_env: dict[str, str] = {}
    if env_file:
        merged_env.update(load_env_file(env_file))
    if env:
        merged_env.update(env)
    token = unique or _unique_token()
    if expand:
        raw = expand_obj(raw, merged_env, token)
    return DemoPlan.model_validate(raw)


def validate_plan_summary(
    path: Path | str,
    *,
    env_file: Path | None = None,
) -> dict[str, Any]:
    plan = load_plan(path, env_file=env_file, expand=True)
    estimate = plan.estimate_seconds()
    return {
        "path": str(path),
        "valid": True,
        "title": plan.title,
        "target": plan.target,
        "auth": plan.auth,
        "voice": plan.voice.model_dump(),
        "video": plan.video.model_dump(),
        "estimate": estimate,
        "chapters": [
            {
                "title": ch.title,
                "scene_ids": [s.id for s in ch.scenes],
            }
            for ch in plan.chapters
        ],
    }
