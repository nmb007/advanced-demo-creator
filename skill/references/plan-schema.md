# Plan schema (`demos/<name>.yaml`)

```yaml
title: Signing in and creating a course
target: local                  # key in .demo/profile.yaml, or full URL
auth: admin-local              # optional saved session label
voice: { engine: kokoro, name: am_michael, speed: 1.0 }
video: { width: 1920, height: 1080, fps: 30, scale: 2 }
chapters:
  - title: Signing in
    scenes:
      - id: login
        start_url: /login/index.php
        narration: "Let's start by signing in with an administrator account."
        pace: spread             # spread | front | back
        hold_after: 0.5
        steps:
          - { action: fill, target: { label: Username }, value: "${DEMO_USER}" }
          - { action: fill, target: { label: Password }, value: "${DEMO_PASS}", mask: true }
          - { action: click, target: { role: button, name: Log in }, zoom: auto }
          - { action: wait_for, target: { text: Dashboard } }
```

## Targets

Prefer in this order:

1. `{ testid: "..." }`
2. `{ role: button, name: "Log in" }`
3. `{ label: "Username" }`
4. `{ text: "Dashboard" }`
5. `{ css: "#id" }` (last resort)

Add `frame: "iframe#preview"` (or iframe name/URL fragment) for elements inside iframes.

## Actions

`goto`, `click`, `fill`, `type` (key-by-key), `select`, `check`, `hover`, `press`,
`scroll`, `wait_for`, `wait` (needs `ms`), `highlight`.

## Zoom

Per step: `auto` (default for click/fill/type), `off`, or a number like `1.6`.

## Variables

- `${ENV_VAR}` — from `.demo` `env_file` or the process environment.
- `${UNIQUE}` — short timestamp (`MMDD-HHMM`) for unique names on remote sites.
- `mask: true` — never log the value.

## Scene rules for long demos

- Every scene should set `start_url` so it can be re-recorded alone.
- Group into chapters; the MP4 gets chapter markers.
- Keep narration ~150 words/minute.
