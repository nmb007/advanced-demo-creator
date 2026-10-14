"""End-to-end render against the static fixture app (requires say + ffmpeg + chromium)."""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

FIXTURE_APP = Path(__file__).parent / "fixtures" / "app"
FIXTURE_PLAN = Path(__file__).parent / "fixtures" / "plan.yaml"


def _have_deps() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    if not shutil.which("say"):
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def fixture_server():
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURE_APP))
    server = ThreadingHTTPServer(("127.0.0.1", 8765), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:8765"
    server.shutdown()


@pytest.mark.skipif(not _have_deps(), reason="ffmpeg/say/chromium not available")
def test_render_fixture_plan(tmp_path: Path, fixture_server: str):
    from demo_creator.pipeline import render_plan

    plan_path = tmp_path / "plan.yaml"
    plan_path.write_text(FIXTURE_PLAN.read_text(encoding="utf-8"), encoding="utf-8")
    project = tmp_path

    import asyncio

    result = asyncio.run(
        render_plan(
            plan_path,
            project_root=project,
            headless=True,
            force=True,
        )
    )
    assert result.get("ok") is True, result
    assembled = result["assemble"]
    out = Path(assembled["output"])
    assert out.is_file()
    assert assembled["duration"] > 2.0
    assert len(assembled["chapters"]) == 2

    # Probe with ffprobe
    ffprobe = shutil.which("ffprobe")
    assert ffprobe
    meta = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height",
            "-of",
            "json",
            str(out),
        ],
        text=True,
    )
    data = json.loads(meta)
    codecs = {s.get("codec_type") for s in data.get("streams", [])}
    assert "video" in codecs
    assert "audio" in codecs
    video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    assert video_stream["width"] == 1280
    assert video_stream["height"] == 720
