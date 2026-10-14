"""Interactive auth session capture for SSO / 2FA / magic links."""

from __future__ import annotations

import time
from pathlib import Path

from demo_creator.browser.session import auth_state_path, browser_session, save_storage_state


async def save_auth(
    label: str,
    start_url: str,
    *,
    done_when_url: str = "",
    done_when_selector: str = "",
    timeout_seconds: int = 300,
) -> dict:
    """Open a headed browser; user logs in; storage state is saved."""
    async with browser_session(headless=False) as (_browser, context, page):
        await page.goto(start_url, wait_until="domcontentloaded")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if done_when_url and done_when_url in page.url:
                break
            if done_when_selector:
                try:
                    if await page.locator(done_when_selector).count() > 0:
                        break
                except Exception:
                    pass
            # If neither condition set, wait for user to close tab / manually confirm via timeout poll
            if not done_when_url and not done_when_selector:
                # Poll until navigation away from start host path or timeout; user presses Enter externally.
                # We check every second; after 2s of idle on a non-start URL we accept.
                if page.url.rstrip("/") != start_url.rstrip("/") and "login" not in page.url.lower():
                    await page.wait_for_timeout(1500)
                    break
            await page.wait_for_timeout(1000)
        else:
            raise TimeoutError(
                f"Auth session '{label}' timed out after {timeout_seconds}s. "
                "Pass done_when_url or done_when_selector to detect success."
            )

        path = await save_storage_state(context, label)
        return {
            "label": label,
            "path": str(path),
            "final_url": page.url,
        }


def auth_exists(label: str) -> bool:
    return auth_state_path(label).is_file()


def list_auth_sessions() -> list[Path]:
    return sorted(auth_state_path("x").parent.glob("*.json"))
