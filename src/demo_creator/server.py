"""FastMCP server exposing demo-creator tools to Cursor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from demo_creator.browser.auth import save_auth as save_auth_session
from demo_creator.browser.probe import probe_page as probe_page_impl
from demo_creator.pipeline import (
    assemble_plan,
    extract_run_frames,
    record_plan,
    render_plan,
    synthesize_plan,
)
from demo_creator.plan.loader import validate_plan_summary
from demo_creator.profile import find_project_root, load_profile, resolve_target_url

mcp = FastMCP(
    name="demo-creator",
    instructions=(
        "Record narrated demo videos of any web app. "
        "Write a demos/<name>.yaml plan, ask the user to approve it once via validate_plan, "
        "then call synthesize → record → extract_frames → assemble (or render)."
    ),
)


def _root(project_root: str | None = None) -> Path:
    return Path(project_root).resolve() if project_root else find_project_root()


@mcp.tool
async def probe_page(
    url: str,
    target: str | None = None,
    auth: str | None = None,
    screenshot: bool = True,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Probe a live page: title, stable selectors, accessibility snapshot, screenshot.

    If `target` is a profile key (e.g. local), `url` may be a path joined to that base.
    """
    root = _root(project_root)
    profile = load_profile(root)
    final_url = url
    if target or (url.startswith("/") and profile.targets):
        base, cfg = resolve_target_url(target or "local", profile)
        if url.startswith("/"):
            final_url = base.rstrip("/") + url
        elif not url.startswith("http"):
            final_url = base.rstrip("/") + "/" + url
        auth = auth or (cfg.auth if cfg else auth)
    shot = root / ".demo" / "probe.png"
    return await probe_page_impl(
        final_url, auth=auth, screenshot=screenshot, screenshot_path=shot
    )


@mcp.tool
async def save_auth(
    label: str,
    start_url: str,
    done_when_url: str = "",
    done_when_selector: str = "",
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Open a headed browser so the user can log in (SSO/2FA). Saves storage state by label."""
    return await save_auth_session(
        label,
        start_url,
        done_when_url=done_when_url,
        done_when_selector=done_when_selector,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool
def validate_plan(plan_path: str, project_root: str | None = None) -> dict[str, Any]:
    """Validate a demos/*.yaml plan and return chapter/scene length estimates for user approval."""
    root = _root(project_root)
    profile = load_profile(root)
    env = None
    if profile.env_file:
        candidate = root / profile.env_file
        env = candidate if candidate.is_file() else None
    path = Path(plan_path)
    if not path.is_absolute():
        path = root / path
    return validate_plan_summary(path, env_file=env)


@mcp.tool
def synthesize(
    plan_path: str,
    scenes: list[str] | None = None,
    run_id: str | None = None,
    force: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Generate Kokoro/say WAV audio for each scene (cached by narration+voice hash)."""
    root = _root(project_root)
    path = Path(plan_path)
    if not path.is_absolute():
        path = root / path
    return synthesize_plan(
        path, project_root=root, run_id=run_id, scenes=scenes, force=force
    )


@mcp.tool
async def record(
    plan_path: str,
    scenes: list[str] | None = None,
    run_id: str | None = None,
    headless: bool = True,
    force: bool = False,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Record each scene with cursor + screencast; returns errors with screenshot on failure."""
    root = _root(project_root)
    path = Path(plan_path)
    if not path.is_absolute():
        path = root / path
    return await record_plan(
        path,
        project_root=root,
        run_id=run_id,
        scenes=scenes,
        headless=headless,
        force=force,
    )


@mcp.tool
def extract_frames(
    run_id: str,
    scene_id: str | None = None,
    every_s: float = 2.0,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Extract sample PNGs from scene/final videos for visual QA."""
    root = _root(project_root)
    return extract_run_frames(root, run_id, scene_id=scene_id, every_s=every_s)


@mcp.tool
def assemble(
    plan_path: str,
    run_id: str | None = None,
    output: str | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Join scenes, mux padded narration audio, write chapter markers → demos/out/<name>.mp4."""
    root = _root(project_root)
    path = Path(plan_path)
    if not path.is_absolute():
        path = root / path
    out = Path(output) if output else None
    return assemble_plan(path, project_root=root, run_id=run_id, output=out)


@mcp.tool
async def render(
    plan_path: str,
    headless: bool = True,
    force: bool = False,
    output: str | None = None,
    project_root: str | None = None,
) -> dict[str, Any]:
    """Shortcut: synthesize + record + assemble, reusing scene caches."""
    root = _root(project_root)
    path = Path(plan_path)
    if not path.is_absolute():
        path = root / path
    out = Path(output) if output else None
    return await render_plan(
        path, project_root=root, headless=headless, force=force, output=out
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
