"""Record a single scene: actions + screencast + timeline + render."""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from demo_creator.browser.actions import run_step
from demo_creator.browser.capture import ScreencastCapture
from demo_creator.browser.session import browser_session, ensure_cursor
from demo_creator.plan.schema import DemoPlan, Scene
from demo_creator.recorder.pacing import step_start_times
from demo_creator.recorder.timeline import Timeline
from demo_creator.runs.cache import RunStore, scene_audio_hash, scene_video_hash
from demo_creator.video.render import render_from_webm, render_scene_video


ProgressCb = Callable[[str, dict], None]


async def record_scene(
    plan: DemoPlan,
    scene: Scene,
    *,
    store: RunStore,
    base_url: str,
    auth_label: str | None,
    headless: bool = True,
    force: bool = False,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    def progress(msg: str, **extra: Any) -> None:
        if on_progress:
            on_progress(msg, {"scene_id": scene.id, **extra})

    audio_path = store.audio_path(scene.id)
    meta = store.read_scene_meta(scene.id)
    audio_duration = float(meta.get("audio_duration") or 3.0)
    if audio_path.is_file():
        import wave

        with wave.open(str(audio_path), "rb") as wf:
            audio_duration = wf.getnframes() / float(wf.getframerate())

    video_settings = plan.video.model_dump()
    if (
        not force
        and store.video_cached(
            scene,
            base_url=base_url,
            audio_duration=audio_duration,
            video_settings=video_settings,
        )
    ):
        progress("cache_hit")
        return {
            "scene_id": scene.id,
            "cached": True,
            "video": str(store.video_path(scene.id)),
            "audio_duration": audio_duration,
        }

    lead_in = plan.lead_in_ms / 1000.0
    target_duration = audio_duration + lead_in + scene.hold_after
    start_targets = step_start_times(scene, audio_duration, lead_in=lead_in)
    frames_dir = store.frames_dir(scene.id)
    # Clear old frames
    for old in frames_dir.glob("frame_*.jpg"):
        old.unlink()
    index = frames_dir / "index.json"
    if index.exists():
        index.unlink()

    timeline = Timeline(
        t0=0.0,
        width=plan.video.width,
        height=plan.video.height,
        scale=plan.video.scale,
    )
    error: dict[str, Any] | None = None
    webm_fallback: Path | None = None

    progress("recording_start")
    async with browser_session(
        headless=headless,
        width=plan.video.width,
        height=plan.video.height,
        scale=plan.video.scale,
        auth_label=auth_label,
        record_video_dir=store.scene_dir(scene.id) / "pw_video",
    ) as (_browser, _ctx, page):
        capture: ScreencastCapture | None = None
        try:
            capture = ScreencastCapture(page, frames_dir)
            await capture.start()
        except Exception as exc:
            progress("screencast_unavailable", error=str(exc))
            capture = None

        timeline.t0 = time.perf_counter()
        try:
            # Navigate to start_url
            start = scene.start_url or "/"
            if start.startswith("http"):
                url = start
            else:
                url = base_url.rstrip("/") + "/" + start.lstrip("/")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await ensure_cursor(page)
            await page.wait_for_timeout(int(plan.lead_in_ms))

            for i, step in enumerate(scene.steps):
                # Catch-up pacing: wait until this step's narration slot if ahead.
                if i < len(start_targets):
                    elapsed = time.perf_counter() - timeline.t0
                    wait_s = start_targets[i] - elapsed
                    if wait_s > 0.01:
                        await page.wait_for_timeout(int(wait_s * 1000))
                try:
                    await run_step(
                        page,
                        step,
                        base_url=base_url,
                        timeline=timeline,
                        step_index=i,
                    )
                except Exception as step_exc:
                    err_path = store.error_path(scene.id)
                    try:
                        await page.screenshot(path=str(err_path), full_page=False)
                    except Exception:
                        pass
                    try:
                        snap = await page.locator("body").aria_snapshot()
                    except Exception:
                        snap = ""
                    error = {
                        "step_index": i,
                        "action": step.action,
                        "error": str(step_exc),
                        "traceback": traceback.format_exc()[-2000:],
                        "screenshot": str(err_path),
                        "accessibility": (snap or "")[:8000],
                        "url": page.url,
                    }
                    progress("step_failed", **error)
                    break

            # Hold until target duration
            elapsed = time.perf_counter() - timeline.t0
            remaining = target_duration - elapsed
            if remaining > 0 and error is None:
                await page.wait_for_timeout(int(remaining * 1000))

        finally:
            if capture:
                await capture.stop()
            # Grab playwright video path if any
            try:
                video = page.video
                if video:
                    webm_fallback = Path(await video.path())
            except Exception:
                pass

    timeline.save(store.timeline_path(scene.id))

    if error:
        store.write_scene_meta(
            scene.id,
            {
                **meta,
                "error": error,
                "audio_duration": audio_duration,
            },
        )
        return {"scene_id": scene.id, "ok": False, "error": error}

    # Render
    progress("rendering")
    out_video = store.video_path(scene.id)
    final_duration = max(target_duration, timeline.duration() + scene.hold_after)
    try:
        if (frames_dir / "index.json").is_file() and list(frames_dir.glob("frame_*.jpg")):
            render_scene_video(
                frames_dir,
                store.timeline_path(scene.id),
                out_video,
                duration=final_duration,
                width=plan.video.width,
                height=plan.video.height,
                fps=plan.video.fps,
                css_w=plan.video.width,
                css_h=plan.video.height,
            )
        elif webm_fallback and webm_fallback.is_file():
            render_from_webm(
                webm_fallback,
                store.timeline_path(scene.id),
                out_video,
                duration=final_duration,
                width=plan.video.width,
                height=plan.video.height,
            )
        else:
            raise RuntimeError("No frames and no WebM fallback for scene render")
    except Exception as render_exc:
        return {
            "scene_id": scene.id,
            "ok": False,
            "error": {"error": str(render_exc), "traceback": traceback.format_exc()[-2000:]},
        }

    vhash = scene_video_hash(
        scene,
        base_url=base_url,
        audio_duration=audio_duration,
        video_settings=video_settings,
    )
    store.write_scene_meta(
        scene.id,
        {
            **meta,
            "audio_duration": audio_duration,
            "video_hash": vhash,
            "audio_hash": meta.get("audio_hash") or scene_audio_hash(scene, plan.voice),
            "duration": final_duration,
            "error": None,
        },
    )
    progress("recording_done", video=str(out_video), duration=final_duration)
    return {
        "scene_id": scene.id,
        "ok": True,
        "cached": False,
        "video": str(out_video),
        "duration": final_duration,
        "audio_duration": audio_duration,
    }
