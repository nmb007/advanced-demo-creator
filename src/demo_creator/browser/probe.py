"""Probe a live page for title, selectors, and optional screenshot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from demo_creator.browser.session import browser_session


async def probe_page(
    url: str,
    *,
    auth: str | None = None,
    screenshot: bool = True,
    screenshot_path: Path | None = None,
    width: int = 1920,
    height: int = 1080,
    scale: int = 2,
    headless: bool = True,
) -> dict[str, Any]:
    async with browser_session(
        headless=headless,
        width=width,
        height=height,
        scale=scale,
        auth_label=auth,
    ) as (_browser, _ctx, page):
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(500)
        title = await page.title()
        status = response.status if response else None

        selectors = await page.evaluate(
            """() => {
              const out = [];
              const seen = new Set();
              const push = (item) => {
                const key = JSON.stringify(item);
                if (seen.has(key) || out.length >= 80) return;
                seen.add(key);
                out.push(item);
              };
              document.querySelectorAll('[data-testid]').forEach(el => {
                push({ kind: 'testid', testid: el.getAttribute('data-testid'), tag: el.tagName.toLowerCase() });
              });
              document.querySelectorAll('button, a, input, select, textarea, [role]').forEach(el => {
                const role = el.getAttribute('role') || ({
                  BUTTON: 'button', A: 'link', INPUT: 'textbox', SELECT: 'combobox', TEXTAREA: 'textbox'
                })[el.tagName];
                const name = (el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('placeholder') || '').trim().slice(0, 80);
                if (role && name) push({ kind: 'role', role, name, tag: el.tagName.toLowerCase() });
                const label = el.labels && el.labels[0] ? el.labels[0].innerText.trim().slice(0, 80) : null;
                if (label) push({ kind: 'label', label, tag: el.tagName.toLowerCase() });
              });
              return out;
            }"""
        )

        # Trimmed accessibility snapshot via Playwright
        try:
            snapshot = await page.locator("body").aria_snapshot()
            if len(snapshot) > 12000:
                snapshot = snapshot[:12000] + "\n…(truncated)"
        except Exception:
            snapshot = ""

        shot_path = None
        if screenshot:
            dest = screenshot_path or (Path.cwd() / ".demo" / "probe.png")
            dest.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(dest), full_page=False)
            shot_path = str(dest)

        return {
            "url": page.url,
            "title": title,
            "status": status,
            "selectors": selectors,
            "accessibility": snapshot,
            "screenshot": shot_path,
        }
