"""Resolve targets and perform plan steps with a visible cursor."""

from __future__ import annotations

import math
import time
from typing import Any

from playwright.async_api import Frame, Locator, Page

from demo_creator.browser.session import ensure_cursor
from demo_creator.plan.schema import Step, Target
from demo_creator.recorder.timeline import Timeline


def fitts_ms(distance: float, target_size: float = 32.0) -> int:
    """Movement time ~ Fitts's law, clamped to 350–900 ms."""
    a, b = 80.0, 140.0
    d = max(distance, 1.0)
    w = max(target_size, 8.0)
    ms = a + b * math.log2(1 + d / w)
    return int(max(350, min(900, ms)))


async def resolve_frame(page: Page, frame_sel: str | None) -> Page | Frame:
    if not frame_sel:
        return page
    # Prefer CSS selector matching an iframe element.
    try:
        handle = await page.wait_for_selector(f"iframe{frame_sel}" if frame_sel.startswith("[") else frame_sel, timeout=5000)
        if handle:
            fr = await handle.content_frame()
            if fr:
                return fr
    except Exception:
        pass
    for fr in page.frames:
        if frame_sel in (fr.name or "") or frame_sel in (fr.url or ""):
            return fr
    raise RuntimeError(f"iframe not found: {frame_sel}")


async def resolve_locator(page: Page, target: Target) -> Locator:
    root = await resolve_frame(page, target.frame)
    if target.testid:
        return root.get_by_test_id(target.testid)
    if target.label:
        return root.get_by_label(target.label, exact=False)
    if target.role:
        kwargs: dict[str, Any] = {}
        if target.name:
            kwargs["name"] = target.name
        return root.get_by_role(target.role, **kwargs)
    if target.text:
        return root.get_by_text(target.text, exact=False)
    if target.css:
        return root.locator(target.css)
    raise RuntimeError("empty target")


async def cursor_move_to(page: Page, x: float, y: float, ms: int) -> None:
    await ensure_cursor(page)
    await page.evaluate(
        """async ([x, y, ms]) => {
          if (!window.__demoCreatorCursor) throw new Error('demo cursor missing');
          await window.__demoCreatorCursor.moveTo(x, y, ms);
        }""",
        [x, y, ms],
    )


async def cursor_press(page: Page) -> None:
    await ensure_cursor(page)
    await page.evaluate(
        """async () => {
          if (!window.__demoCreatorCursor) throw new Error('demo cursor missing');
          await window.__demoCreatorCursor.press();
        }"""
    )


async def cursor_hover(page: Page) -> None:
    await ensure_cursor(page)
    await page.evaluate(
        """async () => {
          if (!window.__demoCreatorCursor) throw new Error('demo cursor missing');
          await window.__demoCreatorCursor.hover();
        }"""
    )


async def box_center(locator: Locator) -> tuple[float, float, dict]:
    box = await locator.bounding_box()
    if not box:
        raise RuntimeError("element has no bounding box (not visible?)")
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, box


async def move_cursor_to_locator(page: Page, locator: Locator, timeline: Timeline | None = None) -> dict:
    x, y, box = await box_center(locator)
    # Current cursor pos (best-effort)
    try:
        pos = await page.evaluate(
            "() => window.__demoCreatorCursor ? window.__demoCreatorCursor.getPos() : {x:0,y:0}"
        )
        dist = math.hypot(x - pos.get("x", 0), y - pos.get("y", 0))
    except Exception:
        dist = 400.0
    ms = fitts_ms(dist, box.get("width", 32))
    t0 = time.perf_counter()
    await cursor_move_to(page, x, y, ms)
    # Avoid Playwright mouse.move — Chromium screencast may paint its own
    # pointer on top of our post-composited cursor. Real clicks still use
    # locator.click/fill, which move the input mouse briefly at action time.
    if timeline is not None:
        timeline.add_cursor_path(t0, time.perf_counter(), x, y, box)
    return box


async def run_step(
    page: Page,
    step: Step,
    *,
    base_url: str,
    timeline: Timeline | None = None,
    step_index: int = 0,
) -> None:
    t_start = time.perf_counter()
    box: dict | None = None
    action = step.action

    if action == "goto":
        url = step.url or ""
        if url.startswith("/"):
            url = base_url.rstrip("/") + url
        elif not url.startswith("http"):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(200)
        await ensure_cursor(page)

    elif action == "wait":
        await page.wait_for_timeout(int(step.ms or 0))

    elif action == "wait_for":
        assert step.target
        loc = await resolve_locator(page, step.target)
        await loc.first.wait_for(state="visible", timeout=30000)

    elif action == "press":
        await page.keyboard.press(step.keys or "Enter")

    elif action == "scroll":
        if step.target:
            loc = await resolve_locator(page, step.target)
            await loc.first.scroll_into_view_if_needed()
        else:
            await page.mouse.wheel(0, int(step.value or 400))

    else:
        assert step.target
        loc = (await resolve_locator(page, step.target)).first
        await loc.wait_for(state="visible", timeout=20000)
        await loc.scroll_into_view_if_needed()
        box = await move_cursor_to_locator(page, loc, timeline)

        if action == "hover":
            await cursor_hover(page)
            await loc.hover()

        elif action == "highlight":
            await loc.evaluate(
                """el => {
                  el.style.outline = '3px solid #2563eb';
                  el.style.outlineOffset = '2px';
                }"""
            )

        elif action == "click":
            await cursor_hover(page)
            await cursor_press(page)
            await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

        elif action == "fill":
            await cursor_press(page)
            await loc.click()
            value = step.value or ""
            await loc.fill(value)

        elif action == "type":
            await cursor_press(page)
            await loc.click()
            value = step.value or ""
            await loc.fill("")
            await loc.type(value, delay=45)

        elif action == "select":
            await cursor_press(page)
            await loc.select_option(step.value)

        elif action == "check":
            await cursor_press(page)
            await loc.check()

        else:
            raise RuntimeError(f"unknown action: {action}")

    if step.hold_ms:
        await page.wait_for_timeout(step.hold_ms)

    if timeline is not None:
        timeline.add_step(
            index=step_index,
            action=action,
            t_start=t_start,
            t_end=time.perf_counter(),
            box=box,
            zoom=step.effective_zoom(),
            masked=step.mask,
        )
