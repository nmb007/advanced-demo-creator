"""Chrome CDP screencast capture (JPEG frames + timestamps)."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.async_api import Page


@dataclass
class FrameBuffer:
    frames_dir: Path
    frames: list[dict[str, Any]] = field(default_factory=list)
    t0: float = 0.0
    _index: int = 0

    def add(self, jpeg: bytes, timestamp: float) -> Path:
        self._index += 1
        path = self.frames_dir / f"frame_{self._index:06d}.jpg"
        path.write_bytes(jpeg)
        rel = timestamp - self.t0 if self.t0 else 0.0
        self.frames.append({"path": str(path), "t": rel, "index": self._index})
        return path

    def save_index(self) -> Path:
        path = self.frames_dir / "index.json"
        path.write_text(
            json.dumps({"t0": self.t0, "frames": self.frames}, indent=2),
            encoding="utf-8",
        )
        return path


class ScreencastCapture:
    """Streams Page.screencastFrame JPEGs into frames_dir."""

    def __init__(self, page: Page, frames_dir: Path, *, quality: int = 90):
        self.page = page
        self.frames_dir = frames_dir
        self.quality = quality
        self.buffer = FrameBuffer(frames_dir=frames_dir)
        self._cdp = None
        self._active = False
        self._queue: asyncio.Queue | None = None
        self._worker: asyncio.Task | None = None

    async def start(self) -> None:
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.buffer.t0 = time.perf_counter()
        self._queue = asyncio.Queue()
        self._cdp = await self.page.context.new_cdp_session(self.page)
        loop = asyncio.get_running_loop()

        def on_frame(params: dict) -> None:
            # Called from Playwright sync callback; schedule onto event loop.
            if not self._queue:
                return
            loop.call_soon_threadsafe(self._queue.put_nowait, params)

        self._cdp.on("Page.screencastFrame", on_frame)
        self._worker = asyncio.create_task(self._drain())
        await self._cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": self.quality,
                "everyNthFrame": 1,
            },
        )
        self._active = True

    async def _drain(self) -> None:
        assert self._queue is not None
        while True:
            params = await self._queue.get()
            if params is None:
                break
            try:
                data = params.get("data")
                if data:
                    jpeg = base64.b64decode(data)
                    self.buffer.add(jpeg, time.perf_counter())
                session_id = params.get("sessionId")
                if self._cdp and session_id is not None:
                    await self._cdp.send(
                        "Page.screencastFrameAck", {"sessionId": session_id}
                    )
            except Exception:
                pass

    async def stop(self) -> FrameBuffer:
        if self._cdp and self._active:
            try:
                await self._cdp.send("Page.stopScreencast")
            except Exception:
                pass
            self._active = False
        if self._queue is not None:
            await self._queue.put(None)
        if self._worker:
            try:
                await asyncio.wait_for(self._worker, timeout=5)
            except Exception:
                self._worker.cancel()
        self.buffer.save_index()
        return self.buffer
