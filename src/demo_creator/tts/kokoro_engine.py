"""Kokoro-82M local TTS engine (optional dependency)."""

from __future__ import annotations

from pathlib import Path

import numpy as np


class KokoroEngine:
    name = "kokoro"
    _pipeline = None

    def available(self) -> bool:
        try:
            import kokoro  # noqa: F401

            return True
        except ImportError:
            return False

    def warmup(self) -> None:
        self._get_pipeline()

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from kokoro import KPipeline
        except ImportError as exc:
            raise RuntimeError(
                "kokoro is not installed. Run: pip install 'demo-creator[kokoro]' "
                "or use voice.engine: say"
            ) from exc
        # American English
        self._pipeline = KPipeline(lang_code="a")
        return self._pipeline

    def synthesize(self, text: str, out_path: Path, *, voice: str, speed: float = 1.0) -> float:
        import soundfile as sf

        out_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline = self._get_pipeline()
        chunks: list[np.ndarray] = []
        sample_rate = 24000
        for result in pipeline(text, voice=voice, speed=speed):
            # KPipeline yields (graphemes, phonemes, audio)
            audio = result.audio if hasattr(result, "audio") else result[-1]
            if audio is None:
                continue
            if hasattr(audio, "numpy"):
                audio = audio.numpy()
            chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            # Silent 0.5s placeholder so pipeline doesn't break
            audio_out = np.zeros(int(sample_rate * 0.5), dtype=np.float32)
        else:
            audio_out = np.concatenate(chunks)
        sf.write(str(out_path), audio_out, sample_rate)
        return float(len(audio_out) / sample_rate)
