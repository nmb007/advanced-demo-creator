"""Compute when each step should start so actions stay aligned with narration."""

from __future__ import annotations

from demo_creator.plan.schema import PaceMode, Scene


def step_start_times(
    scene: Scene,
    audio_duration: float,
    *,
    lead_in: float = 0.3,
) -> list[float]:
    """
    Absolute times (seconds from scene start, including lead-in) when each step
    should begin. The recorder waits until each target if it is ahead of schedule.
    """
    n = len(scene.steps)
    if n == 0:
        return []

    available = max(0.0, audio_duration - lead_in - scene.hold_after)
    pace: PaceMode = scene.pace

    if pace == "front":
        # Fire actions ASAP after lead-in; spare narration time sits in hold_after.
        return [lead_in + i * 0.05 for i in range(n)]

    if pace == "back":
        starts = [lead_in + available * 0.8]
        for i in range(1, n):
            starts.append(starts[-1] + 0.05)
        return starts

    # spread: evenly space step *starts* across the narration window.
    # Fast actions get breathing room; slow ones cause later waits to collapse to 0.
    if available <= 0:
        return [lead_in + i * 0.05 for i in range(n)]
    return [lead_in + (i / n) * available for i in range(n)]


def compute_delays(
    scene: Scene,
    audio_duration: float,
    *,
    lead_in: float = 0.3,
    base_action_estimate: float = 1.2,
) -> list[float]:
    """
    Return a delay (seconds) to sleep BEFORE each step, after lead-in.

    Prefer dynamic catch-up via ``step_start_times`` in the recorder. This helper
    remains for tests and callers that precompute static gaps assuming actions
    are instantaneous (so the whole narration window becomes inter-step delay).

    ``base_action_estimate`` is kept for API compatibility and is unused: the old
    estimate-then-spare model zeroed delays whenever step count * estimate ≈ audio
    length, which made dense scenes race ahead of narration.
    """
    del base_action_estimate  # unused; see docstring
    n = len(scene.steps)
    if n == 0:
        return []

    starts = step_start_times(scene, audio_duration, lead_in=lead_in)
    delays: list[float] = []
    prev = lead_in
    for start in starts:
        delays.append(max(0.0, start - prev))
        prev = start
    return delays
