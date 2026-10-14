---
name: demo-creator
description: >-
  Create fully narrated demo videos of any web app from a prompt. Use when the
  user asks to make a demo, product walkthrough, feature tour, tutorial video,
  or narrated recording of a running site. Works with any URL in Chromium.
---

# Demo Creator

Turn a prompt into a narrated MP4 of a running web app. You write the storyboard;
the `demo-creator` MCP records it with a visible cursor, smooth zoom, and local
TTS (Kokoro, with macOS `say` fallback).

## Workflow (always follow this order)

1. **Understand the request.** Classify as:
   - **Flow demo** — a specific user journey (e.g. "sign in and create a course").
   - **Feature tour** — discover and show what the app/theme/plugin exposes.

2. **Discover** — read [references/discovery.md](references/discovery.md):
   - Load `.demo/profile.yaml` if present.
   - Find routes, e2e tests, `data-testid`s, ARIA labels.
   - Call `probe_page` on key URLs to confirm selectors.

3. **Feature tours only** — write `demos/<name>.features.md` listing each feature
   with URL + how to trigger it. Ask the user to trim the list before storyboarding.

4. **Storyboard** — write `demos/<name>.yaml` (see [references/plan-schema.md](references/plan-schema.md)).
   - One plan file per distinct demo. Before creating, check for an existing similar
     `demos/*.yaml` and ask whether to **update** or **create new**.
   - Include chapters, intro/outro, linking lines between chapters.
   - Follow [references/narration-style.md](references/narration-style.md).

5. **Single approval** — call `validate_plan` and show the user:
   - title, chapters, scene ids
   - estimated seconds per chapter and total
   Wait for explicit go-ahead. Do not record until approved.

6. **Run** — `synthesize` then `record` (or `render`).
   - On step failure: read `screenshot` + `accessibility` from the error, fix that
     scene in the YAML, re-`record` with `scenes=[id]` only. Max 3 tries per scene.

7. **QA** — `extract_frames` on the run. Look for error pages, spinners, empty
   states, wrong pages. Redo bad scenes.

8. **Finish** — `assemble` if not already done. Report MP4 path, duration, chapters.
   Offer to save learned URLs/auth/selectors into `.demo/profile.yaml`.

## MCP tools

| Tool | Purpose |
|------|---------|
| `probe_page` | Reachability, selectors, a11y snapshot, screenshot |
| `save_auth` | Headed login for SSO/2FA; saves `~/.demo-creator/auth/<label>.json` |
| `validate_plan` | Schema check + length estimates (approval step) |
| `synthesize` | TTS WAV per scene (cached) |
| `record` | Playwright + cursor + screencast → scene.mp4 |
| `extract_frames` | Sample PNGs for visual QA |
| `assemble` | Join scenes, mux audio, chapter markers |
| `render` | synthesize + record + assemble |

## Project files you create

| Path | Purpose | Commit? |
|------|---------|---------|
| `demos/<name>.yaml` | Storyboard / plan | Yes |
| `demos/<name>.features.md` | Feature inventory | Optional |
| `demos/out/<name>.mp4` | Final video | Usually no |
| `.demo/profile.yaml` | Targets, auth, hooks | Yes |
| `.demo/runs/` | Cache (auto-gitignored) | No |

## Troubleshooting

See [references/troubleshooting.md](references/troubleshooting.md).
