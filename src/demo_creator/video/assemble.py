"""Join scene videos, pad/mux audio, add chapter markers."""

from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np

from demo_creator.plan.schema import DemoPlan
from demo_creator.runs.cache import RunStore
from demo_creator.video.chapters import write_ffmetadata
from demo_creator.video.render import find_ffmpeg


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def _pad_wav(src: Path, dest: Path, target_seconds: float, lead_in: float = 0.3) -> float:
    """Pad/trim WAV to target_seconds with lead-in silence. Returns final duration."""
    import soundfile as sf

    data, sr = sf.read(str(src), always_2d=True)
    lead = np.zeros((int(sr * lead_in), data.shape[1]), dtype=data.dtype)
    combined = np.concatenate([lead, data], axis=0)
    target_samples = int(sr * target_seconds)
    if len(combined) < target_samples:
        pad = np.zeros((target_samples - len(combined), data.shape[1]), dtype=data.dtype)
        combined = np.concatenate([combined, pad], axis=0)
    else:
        combined = combined[:target_samples]
    sf.write(str(dest), combined, sr)
    return len(combined) / sr


def _probe_duration(path: Path) -> float:
    ffmpeg = find_ffmpeg()
    # use ffprobe if available else ffmpeg
    import shutil

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        out = subprocess.check_output(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        )
        return float(out.strip())
    # Fallback: decode with soundfile not applicable; assume from meta
    return 0.0


def assemble_run(
    store: RunStore,
    plan: DemoPlan,
    *,
    output: Path | None = None,
) -> dict[str, Any]:
    ffmpeg = find_ffmpeg()
    scenes = plan.all_scenes()
    work = store.run_dir / "assemble"
    work.mkdir(parents=True, exist_ok=True)

    scene_durations: list[float] = []
    concat_list = work / "concat.txt"
    padded_audio_parts: list[Path] = []

    lines = []
    for scene in scenes:
        video = store.video_path(scene.id)
        audio = store.audio_path(scene.id)
        if not video.is_file():
            raise FileNotFoundError(f"missing scene video: {video}")
        meta = store.read_scene_meta(scene.id)
        audio_dur = float(meta.get("audio_duration") or ( _wav_duration(audio) if audio.is_file() else 3.0))
        # Video should already be >= audio + hold; use max of video probe and audio target
        vid_dur = _probe_duration(video) or audio_dur + scene.hold_after + plan.lead_in_ms / 1000.0
        target = max(vid_dur, audio_dur + plan.lead_in_ms / 1000.0 + scene.hold_after)
        scene_durations.append(target)

        # Ensure video length by padding with last frame if needed
        padded_video = work / f"{scene.id}.mp4"
        if vid_dur + 0.05 < target:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(video),
                    "-vf",
                    f"tpad=stop_mode=clone:stop_duration={target - vid_dur}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-crf",
                    "18",
                    "-an",
                    str(padded_video),
                ],
                check=True,
                capture_output=True,
            )
        else:
            # trim/copy
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(video),
                    "-t",
                    str(target),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-crf",
                    "18",
                    "-an",
                    str(padded_video),
                ],
                check=True,
                capture_output=True,
            )
        lines.append(f"file '{padded_video.resolve()}'")

        if audio.is_file():
            padded = work / f"{scene.id}.wav"
            _pad_wav(audio, padded, target, lead_in=plan.lead_in_ms / 1000.0)
            padded_audio_parts.append(padded)

    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    silent_video = work / "video_silent.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(silent_video),
        ],
        check=True,
        capture_output=True,
    )

    # Concatenate audio
    full_audio = work / "audio.wav"
    if padded_audio_parts:
        import soundfile as sf

        pieces = []
        sr = None
        for part in padded_audio_parts:
            data, rate = sf.read(str(part), always_2d=True)
            sr = rate
            pieces.append(data)
        sf.write(str(full_audio), np.concatenate(pieces, axis=0), sr)

    # Chapters
    chapters_meta: list[tuple[str, float, float]] = []
    t = 0.0
    idx = 0
    for chapter in plan.chapters:
        start = t
        for _scene in chapter.scenes:
            t += scene_durations[idx]
            idx += 1
        chapters_meta.append((chapter.title, start, t))
    meta_file = work / "chapters.txt"
    write_ffmetadata(meta_file, chapters_meta)

    if output is None:
        out_dir = store.project_root / "demos" / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = Path(store.read_meta().get("plan_path", "demo")).stem
        output = out_dir / f"{slug}.mp4"

    output.parent.mkdir(parents=True, exist_ok=True)
    if full_audio.is_file():
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(full_audio),
            "-i",
            str(meta_file),
            "-map_metadata",
            "2",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ]
    else:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(meta_file),
            "-map_metadata",
            "1",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ]
    subprocess.run(cmd, check=True, capture_output=True)

    result = {
        "output": str(output),
        "duration": sum(scene_durations),
        "chapters": [
            {"title": t, "start": s, "end": e} for t, s, e in chapters_meta
        ],
        "run_id": store.run_id,
    }
    store.write_meta({"assembled": result})
    (store.run_dir / "assemble_result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result
