# Troubleshooting

| Symptom | Fix |
|---------|-----|
| Element not found | `probe_page` with screenshot; prefer testid/role; check `frame` for iframes |
| Blank / spinner frames | Add `wait_for` before click; increase `hold_after` |
| Auth expired | Re-run `save_auth`; check `auth` label in plan |
| ffmpeg missing | `brew install ffmpeg` then `demo-creator doctor` |
| Chromium missing | `demo-creator install` or `playwright install chromium` |
| Kokoro unavailable | Installs fall back to macOS `say`; or `pip install 'demo-creator[kokoro]'` |
| Timing drift | Edit narration length or `pace` / `hold_after`; re-`synthesize` that scene |
| Long demo slow | Scene caches reuse unchanged scenes; only re-record changed ids |
| Remote data collisions | Use `${UNIQUE}` in created names; set `unique_suffix: true` on the target |

Failed steps write `error.png` and an accessibility snapshot into
`.demo/runs/<run_id>/scenes/<id>/`.
