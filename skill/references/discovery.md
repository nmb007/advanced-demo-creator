# Discovery (any web framework)

## Profile first

Read `.demo/profile.yaml` if it exists: targets, auth labels, hooks, selector_sources, login.

## Routes

Search the repo for:

| Stack | Where |
|-------|-------|
| Next.js / Nuxt | `app/`, `pages/` |
| React Router | `createBrowserRouter`, `<Route` |
| Vue Router | `createRouter`, `routes:` |
| Rails | `config/routes.rb` |
| Django | `urls.py` |
| Laravel | `routes/web.php` |
| PHP / Totara | `index.php`, plugin `*_controller`, rewrite rules |
| Generic | sitemap, nav components, README URLs |

Also explore the live app with `probe_page`.

## Selectors

Mine existing tests before inventing selectors:

- Playwright / Cypress: `tests/e2e`, `e2e/`, `cypress/`
- Behat / Selenium: `features/`, `*.feature`
- `data-testid`, `data-test`, `aria-label`
- Translation / lang strings used as button labels

Prefer role+name and labels over CSS paths.

## Feature tours

Also read:

- README, CHANGELOG, docs/
- Settings / admin pages
- Feature flags / config schemas
- Storybook stories
- Theme / plugin manifests (`theme_*`, `version.php`, `package.json` exports)

Produce `demos/<name>.features.md`:

```markdown
# Features: Custom theme

1. **Brand login** — `/login` — custom logo + colours
2. **Dashboard tiles** — `/` after login — enable in theme settings
...
```

Ask the user which items to keep, then storyboard only those.
