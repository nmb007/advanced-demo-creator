"""Filesystem locations used by demo-creator."""

from __future__ import annotations

import os
from pathlib import Path


def home_dir() -> Path:
    override = os.environ.get("DEMO_CREATOR_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".demo-creator"


def auth_dir() -> Path:
    path = home_dir() / "auth"
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    path = home_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def package_root() -> Path:
    return Path(__file__).resolve().parent


def skill_source_dir() -> Path:
    """Skill directory shipped with the package or living next to src in the repo."""
    packaged = package_root() / "skill"
    if packaged.is_dir():
        return packaged
    # Editable / repo checkout: skill/ sits at the repo root.
    repo = package_root().parents[1] / "skill"
    if repo.is_dir():
        return repo
    return packaged


def cursor_mcp_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def cursor_skills_dir() -> Path:
    return Path.home() / ".cursor" / "skills" / "demo-creator"


def project_demo_dir(project_root: Path) -> Path:
    return project_root / ".demo"


def project_runs_dir(project_root: Path) -> Path:
    return project_demo_dir(project_root) / "runs"


def project_demos_dir(project_root: Path) -> Path:
    return project_root / "demos"


def ensure_project_gitignore(project_root: Path) -> None:
    """Append .demo/runs/ to the project's .gitignore if missing."""
    gitignore = project_root / ".gitignore"
    entry = ".demo/runs/"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        if entry in text or ".demo/runs" in text:
            return
        with gitignore.open("a", encoding="utf-8") as fh:
            if text and not text.endswith("\n"):
                fh.write("\n")
            fh.write(f"\n# demo-creator run cache\n{entry}\ndemos/out/\n")
    else:
        gitignore.write_text(
            f"# demo-creator\n{entry}\ndemos/out/\n",
            encoding="utf-8",
        )
