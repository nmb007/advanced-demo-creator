"""Typer CLI: install, doctor, serve, render, runs."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

app = typer.Typer(
    name="demo-creator",
    help="Local AI-narrated demo video creator for any web app.",
    no_args_is_help=True,
)


@app.command()
def install() -> None:
    """Register MCP + skill in Cursor, install Chromium, warm up TTS."""
    from demo_creator.install import run_install

    result = run_install()
    rprint("[green]Installed demo-creator for Cursor.[/green]")
    rprint(json.dumps(result, indent=2))
    rprint("\nRestart Cursor, then ask: [bold]Make a demo of …[/bold]")


@app.command()
def doctor() -> None:
    """Check ffmpeg, Chromium, MCP config, skill, and TTS engines."""
    from demo_creator.install import doctor as run_doctor

    result = run_doctor()
    table = Table(title="demo-creator doctor")
    table.add_column("Check")
    table.add_column("OK")
    table.add_column("Detail")
    for c in result["checks"]:
        table.add_row(c["name"], "yes" if c["ok"] else "NO", c.get("detail") or "")
    rprint(table)
    raise typer.Exit(0 if result["ok"] else 1)


@app.command()
def serve() -> None:
    """Start the MCP server (stdio). Used by Cursor mcp.json."""
    from demo_creator.server import main

    main()


@app.command()
def render(
    plan: Path = typer.Argument(..., help="Path to demos/<name>.yaml"),
    headed: bool = typer.Option(False, "--headed", help="Show the browser"),
    force: bool = typer.Option(False, "--force", help="Ignore scene caches"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    project_root: Optional[Path] = typer.Option(None, "--project"),
) -> None:
    """Synthesize + record + assemble without Cursor (debug)."""
    from demo_creator.pipeline import render_plan
    from demo_creator.profile import find_project_root

    root = project_root or find_project_root(plan.parent)
    result = asyncio.run(
        render_plan(
            plan.resolve(),
            project_root=root.resolve(),
            headless=not headed,
            force=force,
            output=output,
            on_progress=lambda msg, data: rprint(f"[cyan]{msg}[/cyan] {data}"),
        )
    )
    rprint(json.dumps(result, indent=2, default=str))
    raise typer.Exit(0 if result.get("ok") else 1)


@app.command("validate")
def validate_cmd(
    plan: Path = typer.Argument(...),
    project_root: Optional[Path] = typer.Option(None, "--project"),
) -> None:
    """Validate a plan and print length estimates."""
    from demo_creator.plan.loader import validate_plan_summary
    from demo_creator.profile import env_file_path, find_project_root, load_profile

    root = (project_root or find_project_root(plan.parent)).resolve()
    profile = load_profile(root)
    summary = validate_plan_summary(plan.resolve(), env_file=env_file_path(root, profile))
    rprint(json.dumps(summary, indent=2))


@app.command()
def runs(
    project_root: Optional[Path] = typer.Option(None, "--project"),
) -> None:
    """List recent runs under .demo/runs/."""
    from demo_creator.paths import project_runs_dir
    from demo_creator.profile import find_project_root

    root = (project_root or find_project_root()).resolve()
    runs_dir = project_runs_dir(root)
    if not runs_dir.is_dir():
        rprint("No runs yet.")
        raise typer.Exit(0)
    table = Table(title=f"Runs in {runs_dir}")
    table.add_column("run_id")
    table.add_column("title")
    for path in sorted(runs_dir.iterdir(), reverse=True):
        if not path.is_dir():
            continue
        meta_path = path / "meta.json"
        title = ""
        if meta_path.is_file():
            title = json.loads(meta_path.read_text()).get("title", "")
        table.add_row(path.name, title)
    rprint(table)


@app.callback()
def _main() -> None:
    pass


if __name__ == "__main__":
    app()
