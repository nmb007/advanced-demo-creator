"""Run before_record / after_record shell hooks from the app profile."""

from __future__ import annotations

import subprocess
from pathlib import Path

from demo_creator.profile import HooksConfig


class HookError(RuntimeError):
    pass


def run_hook(command: str | None, *, cwd: Path, label: str) -> dict:
    if not command:
        return {"ran": False, "label": label}
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    result = {
        "ran": True,
        "label": label,
        "command": command,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    }
    if proc.returncode != 0:
        raise HookError(
            f"Hook {label} failed ({proc.returncode}): {proc.stderr or proc.stdout}"
        )
    return result


def run_before(hooks: HooksConfig, cwd: Path) -> dict:
    return run_hook(hooks.before_record, cwd=cwd, label="before_record")


def run_after(hooks: HooksConfig, cwd: Path) -> dict:
    return run_hook(hooks.after_record, cwd=cwd, label="after_record")
