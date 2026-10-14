"""Playwright browser session helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from demo_creator.paths import auth_dir, package_root


def cursor_js_path() -> Path:
    return package_root() / "browser" / "cursor.js"


def auth_state_path(label: str) -> Path:
    return auth_dir() / f"{label}.json"


@asynccontextmanager
async def browser_session(
    *,
    headless: bool = True,
    width: int = 1920,
    height: int = 1080,
    scale: int = 2,
    auth_label: str | None = None,
    record_video_dir: Path | None = None,
) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        storage = None
        if auth_label:
            path = auth_state_path(auth_label)
            if path.is_file():
                storage = str(path)

        context_kwargs: dict = {
            "viewport": {"width": width, "height": height},
            "device_scale_factor": scale,
            "storage_state": storage,
        }
        if record_video_dir:
            record_video_dir.mkdir(parents=True, exist_ok=True)
            context_kwargs["record_video_dir"] = str(record_video_dir)
            context_kwargs["record_video_size"] = {"width": width, "height": height}

        context = await browser.new_context(**context_kwargs)
        js = cursor_js_path().read_text(encoding="utf-8")
        await context.add_init_script(js)
        page = await context.new_page()
        try:
            yield browser, context, page
        finally:
            await context.close()
            await browser.close()


async def save_storage_state(context: BrowserContext, label: str) -> Path:
    path = auth_state_path(label)
    await context.storage_state(path=str(path))
    return path
