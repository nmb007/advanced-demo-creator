"""TTS engine interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from demo_creator.plan.schema import VoiceSettings


class TTSEngine(ABC):
    name: str

    @abstractmethod
    def synthesize(self, text: str, out_path: Path, *, voice: str, speed: float = 1.0) -> float:
        """Write WAV to out_path; return duration in seconds."""

    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def warmup(self) -> None:
        """Download models / verify binary."""


def get_engine(settings: VoiceSettings) -> TTSEngine:
    if settings.engine == "say":
        from demo_creator.tts.say_engine import SayEngine

        return SayEngine()
    from demo_creator.tts.kokoro_engine import KokoroEngine

    eng = KokoroEngine()
    if eng.available():
        return eng
    from demo_creator.tts.say_engine import SayEngine

    return SayEngine()
