"""Install MCP + skill into Cursor; doctor checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from demo_creator.paths import (
    cursor_mcp_path,
    cursor_skills_dir,
    home_dir,
    skill_source_dir,
)


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def merge_mcp_config() -> dict[str, Any]:
    path = cursor_mcp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    servers = data.setdefault("mcpServers", {})
    # Prefer the installed console script
    demo_bin = _which("demo-creator") or "demo-creator"
    servers["demo-creator"] = {
        "command": demo_bin,
        "args": ["serve"],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "entry": servers["demo-creator"]}


def install_skill() -> dict[str, Any]:
    src = skill_source_dir()
    dest = cursor_skills_dir()
    if not src.is_dir():
        raise FileNotFoundError(f"Skill source not found: {src}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return {"source": str(src), "dest": str(dest)}


def install_chromium() -> dict[str, Any]:
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
    )
    return {
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-2000:],
        "stderr": (proc.stderr or "")[-2000:],
    }


def warmup_tts() -> dict[str, Any]:
    from demo_creator.plan.schema import VoiceSettings
    from demo_creator.tts.base import get_engine

    engine = get_engine(VoiceSettings())
    try:
        engine.warmup()
        return {"engine": engine.name, "ok": True}
    except Exception as exc:
        # Fall back to say
        from demo_creator.tts.say_engine import SayEngine

        say = SayEngine()
        ok = say.available()
        return {"engine": "say" if ok else engine.name, "ok": ok, "warning": str(exc)}


def run_install() -> dict[str, Any]:
    home_dir().mkdir(parents=True, exist_ok=True)
    result = {
        "mcp": merge_mcp_config(),
        "skill": install_skill(),
        "chromium": install_chromium(),
        "tts": warmup_tts(),
    }
    return result


def doctor() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    check("ffmpeg", _which("ffmpeg") is not None, _which("ffmpeg") or "missing — brew install ffmpeg")
    check(
        "espeak-ng",
        _which("espeak-ng") is not None or _which("espeak") is not None,
        "optional but recommended for Kokoro — brew install espeak-ng",
    )
    check("demo-creator", _which("demo-creator") is not None, _which("demo-creator") or "not on PATH")

    mcp = cursor_mcp_path()
    mcp_ok = False
    if mcp.is_file():
        try:
            data = json.loads(mcp.read_text(encoding="utf-8"))
            mcp_ok = "demo-creator" in (data.get("mcpServers") or {})
        except json.JSONDecodeError:
            mcp_ok = False
    check("mcp.json", mcp_ok, str(mcp))

    skill = cursor_skills_dir() / "SKILL.md"
    check("skill", skill.is_file(), str(skill))

    # Chromium via playwright
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        check("chromium", True, "playwright chromium launches")
    except Exception as exc:
        check("chromium", False, str(exc))

    from demo_creator.tts.kokoro_engine import KokoroEngine
    from demo_creator.tts.say_engine import SayEngine

    kokoro = KokoroEngine()
    say = SayEngine()
    check(
        "kokoro",
        kokoro.available(),
        "optional extra: demo-creator with kokoro dependency group",
    )
    check("say_fallback", say.available(), "macOS say + afconvert")

    # Core runtime readiness (MCP/skill are install-step concerns)
    required = {"ffmpeg", "say_fallback"}
    if not say.available() and not kokoro.available():
        required.add("kokoro")
    return {
        "ok": all(c["ok"] for c in checks if c["name"] in required | {"ffmpeg"}),
        "checks": checks,
        "hint": "Run `demo-creator install` to register MCP + skill and install Chromium.",
    }
