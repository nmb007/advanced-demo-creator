"""High-level synthesize / record / assemble / render orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from demo_creator.hooks import run_after, run_before
from demo_creator.plan.loader import load_plan
from demo_creator.plan.schema import DemoPlan
from demo_creator.profile import (
    env_file_path,
    find_project_root,
    load_profile,
    resolve_target_url,
)
from demo_creator.recorder.scene_runner import record_scene
from demo_creator.runs.cache import RunStore, init_run_for_plan, scene_audio_hash
from demo_creator.tts.base import get_engine
from demo_creator.video.assemble import assemble_run
from demo_creator.video.frames import extract_frames


ProgressCb = Callable[[str, dict], None]


def _resolve_context(plan_path: Path, project_root: Path | None = None):
    root = project_root or find_project_root(plan_path.parent)
    profile = load_profile(root)
    env_path = env_file_path(root, profile)
    plan = load_plan(plan_path, env_file=env_path, expand=True)
    base_url, target_cfg = resolve_target_url(plan.target, profile)
    auth = plan.auth or (target_cfg.auth if target_cfg else None)
    return root, profile, plan, base_url, auth


def synthesize_plan(
    plan_path: Path,
    *,
    project_root: Path | None = None,
    run_id: str | None = None,
    scenes: list[str] | None = None,
    force: bool = False,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    root, _profile, plan, _base, _auth = _resolve_context(plan_path, project_root)
    store = RunStore(root, run_id=run_id) if run_id else init_run_for_plan(root, plan, plan_path)
    store.write_meta({"plan_path": str(plan_path), "title": plan.title})
    engine = get_engine(plan.voice)
    results = []
    for scene in plan.all_scenes():
        if scenes and scene.id not in scenes:
            continue
        if not force and store.audio_cached(scene, plan.voice) and scene.narration:
            meta = store.read_scene_meta(scene.id)
            results.append(
                {
                    "scene_id": scene.id,
                    "cached": True,
                    "duration": meta.get("audio_duration"),
                    "path": str(store.audio_path(scene.id)),
                }
            )
            if on_progress:
                on_progress("audio_cache_hit", {"scene_id": scene.id})
            continue
        text = scene.narration.strip() or " "
        out = store.audio_path(scene.id)
        if on_progress:
            on_progress("synthesizing", {"scene_id": scene.id})
        duration = engine.synthesize(
            text, out, voice=plan.voice.name, speed=plan.voice.speed
        )
        meta = store.read_scene_meta(scene.id)
        meta.update(
            {
                "audio_hash": scene_audio_hash(scene, plan.voice),
                "audio_duration": duration,
            }
        )
        store.write_scene_meta(scene.id, meta)
        results.append(
            {
                "scene_id": scene.id,
                "cached": False,
                "duration": duration,
                "path": str(out),
            }
        )
    return {"run_id": store.run_id, "scenes": results, "engine": engine.name}


async def record_plan(
    plan_path: Path,
    *,
    project_root: Path | None = None,
    run_id: str | None = None,
    scenes: list[str] | None = None,
    headless: bool = True,
    force: bool = False,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    root, profile, plan, base_url, auth = _resolve_context(plan_path, project_root)
    if run_id:
        store = RunStore.open(root, run_id)
    else:
        # Prefer latest run that has audio, else new
        store = RunStore.latest(root) or init_run_for_plan(root, plan, plan_path)
        store.write_meta({"plan_path": str(plan_path), "title": plan.title})

    hook_before = run_before(profile.hooks, root)
    results = []
    try:
        for scene in plan.all_scenes():
            if scenes and scene.id not in scenes:
                continue
            result = await record_scene(
                plan,
                scene,
                store=store,
                base_url=base_url,
                auth_label=auth,
                headless=headless,
                force=force,
                on_progress=on_progress,
            )
            results.append(result)
            if result.get("ok") is False:
                break
    finally:
        hook_after = run_after(profile.hooks, root)

    return {
        "run_id": store.run_id,
        "scenes": results,
        "hooks": {"before": hook_before, "after": hook_after},
        "base_url": base_url,
    }


def assemble_plan(
    plan_path: Path,
    *,
    project_root: Path | None = None,
    run_id: str | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    root, _profile, plan, _base, _auth = _resolve_context(plan_path, project_root)
    store = RunStore.open(root, run_id) if run_id else RunStore.latest(root)
    if not store:
        raise FileNotFoundError("No run found; synthesize and record first")
    return assemble_run(store, plan, output=output)


async def render_plan(
    plan_path: Path,
    *,
    project_root: Path | None = None,
    headless: bool = True,
    force: bool = False,
    output: Path | None = None,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    synth = synthesize_plan(
        plan_path,
        project_root=project_root,
        force=force,
        on_progress=on_progress,
    )
    rec = await record_plan(
        plan_path,
        project_root=project_root,
        run_id=synth["run_id"],
        headless=headless,
        force=force,
        on_progress=on_progress,
    )
    failed = [s for s in rec["scenes"] if s.get("ok") is False]
    if failed:
        return {"ok": False, "synthesize": synth, "record": rec, "failed": failed}
    assembled = assemble_plan(
        plan_path,
        project_root=project_root,
        run_id=synth["run_id"],
        output=output,
    )
    return {"ok": True, "synthesize": synth, "record": rec, "assemble": assembled}


def extract_run_frames(
    project_root: Path,
    run_id: str,
    *,
    scene_id: str | None = None,
    every_s: float = 2.0,
) -> dict[str, Any]:
    store = RunStore.open(project_root, run_id)
    out: dict[str, Any] = {"run_id": run_id, "scenes": {}}
    scene_ids = [scene_id] if scene_id else [
        p.name for p in (store.run_dir / "scenes").iterdir() if p.is_dir()
    ]
    for sid in scene_ids:
        video = store.video_path(sid)
        if not video.is_file():
            continue
        qa_dir = store.scene_dir(sid) / "qa_frames"
        paths = extract_frames(video, qa_dir, every_s=every_s)
        out["scenes"][sid] = paths
    # Also try final assemble output
    meta = store.read_meta()
    assembled = (meta.get("assembled") or {}).get("output")
    if assembled and Path(assembled).is_file() and not scene_id:
        qa = store.run_dir / "qa_frames"
        out["final"] = extract_frames(Path(assembled), qa, every_s=every_s)
    return out
