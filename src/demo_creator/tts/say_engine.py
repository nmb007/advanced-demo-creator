"""macOS `say` TTS fallback."""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path


class SayEngine:
    name = "say"

    def available(self) -> bool:
        return shutil.which("say") is not None and shutil.which("afconvert") is not None

    def warmup(self) -> None:
        if not self.available():
            raise RuntimeError("macOS say/afconvert not available")

    def synthesize(self, text: str, out_path: Path, *, voice: str, speed: float = 1.0) -> float:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        aiff = out_path.with_suffix(".aiff")
        # Map kokoro-ish names to macOS voices when possible
        mac_voice = {
            "am_michael": "Alex",
            "am_adam": "Alex",
            "af_sarah": "Samantha",
            "bf_emma": "Martha",
            "bm_george": "Daniel",
        }.get(voice, voice if voice in ("Alex", "Samantha", "Daniel", "Martha", "Fred") else "Alex")
        rate = int(175 * speed)
        subprocess.run(
            ["say", "-v", mac_voice, "-r", str(rate), "-o", str(aiff), text],
            check=True,
            capture_output=True,
        )
        # Convert AIFF -> WAV
        subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", "LEI16", str(aiff), str(out_path)],
            check=True,
            capture_output=True,
        )
        aiff.unlink(missing_ok=True)
        return _wav_duration(out_path)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())
