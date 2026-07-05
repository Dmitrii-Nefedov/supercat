# DevOps — Supercat Weather

DevOps engineering documentation for the Supercat Weather PWA.

## Infrastructure

### Hosting
- **Platform**: GitHub Pages (static site)
- **Domain**: `https://dmitrii-nefedov.github.io/supercat/`
- **Deployment**: Fully static — no backend, no build step, no server.
- **CDN**: GitHub Pages serves via Fastly edge cache.

### Deployment Pipeline
- **File**: `.github/workflows/deploy.yml`
- **Trigger**: Push to `main` or manual `workflow_dispatch`
- **Flow**: `checkout` → `configure-pages` (with `enablement: true` for auto-setup) → `upload-pages-artifact` → `deploy-pages`
- **Permissions**: `contents: read`, `pages: write`, `id-token: write`
- **Concurrency**: Grouped under `pages` — cancels in-flight deploys on new pushes.
- **Status**: ⏳ Requires manual Pages enablement in repo settings (see [#6](https://github.com/Dmitrii-Nefedov/supercat/issues/6))

### CI Pipeline
- **File**: `.github/workflows/ci.yml`
- **Trigger**: Pull requests targeting `main` and pushes to `main`
- **Jobs** (parallel):
  - **`validate`**: HTML5 validation (via `html5validator-action`) with CSS checks, JSON syntax validation (all `.json` files), service worker integrity check (lifecycle events present), Content-Security-Policy validation (required directives present in `index.html`), JavaScript unit tests (`tests/test_weather.js`), service worker unit tests (`tests/test_sw.js`)
  - **`lint`**: Python linting with `ruff` on `weather.py` — pip cached for faster runs
  - **`test`**: Python tests (`tests/test_weather.py`) with pytest — pip cached for faster runs
- **Caching**: pip cache preserved between runs via `actions/cache@v4` (separate keys per job)
### Test Suites
- **`tests/test_weather.py`** — 95 Python tests covering CLI commands, API mocking, WMO mappings, JSON formatting, hourly forecast
- **`tests/test_weather.js`** — 37 JS tests covering temperature conversion, wind direction, UV index, WMO icons, day names
- **`tests/test_sw.js`** — 22 SW tests covering cache configuration, lifecycle events, fetch strategy, navigation routing, cache cleanup, API fallback handling

### Dependency Automation
- **File**: `.github/dependabot.yml`
- **Scope**: GitHub Actions runners only (no npm/pip deps — pure static site)
- **Schedule**: Weekly, Monday morning
- **PR limit**: Max 10 open PRs at a time

## Monitoring & Observability

No external monitoring is configured for this static site. Recommended additions:
- **Uptime monitoring**: GitHub Pages built-in status page, or external check via Pingdom/Checkly
- **Lighthouse CI**: Add workflow to audit performance/accessibility on deploy
- **Analytics**: Plausible or Umami (self-hosted) for privacy-respecting traffic insights

## Performance

### Current optimizations
- Preconnect hints for Open-Meteo API, Geocoding API, Google Fonts
- DNS-prefetch fallbacks for all external origins
- Render-blocking CSS `@import` replaced with `<link rel=stylesheet>`
- Service worker caches static assets for offline use
- No JavaScript framework overhead — vanilla HTML/CSS/JS

### Targets
| Metric | Target |
|--------|--------|
| First Contentful Paint | < 1.5s |
| Largest Contentful Paint | < 2.5s |
| Time to Interactive | < 3.0s |
| Lighthouse Performance | > 90 |

## Service Worker

- **File**: `sw.js`
- **Strategy**: Cache-first for static assets, network-first for API calls
- **Cache**: Named `supercat-weather-v4`
- **Lifecycle**: `install` → `activate` (clean old caches) → `fetch`
- **Tests**: `tests/test_sw.js` — validates cache configuration, URL routing, lifecycle events, and fallback behavior (16 tests)

## Incident Response

Priority levels for the Supercat Weather app:

| Priority | Definition | Response Time |
|----------|-----------|---------------|
| P1 | App unreachable (DNS / Pages outage) | < 1 hour |
| P2 | Weather data not loading (API issue) | < 4 hours |
| P3 | UI/UX defect, no data loss | < 48 hours |
| P4 | Cosmetic / enhancement | Next sprint |

## Security

- **No secrets in repo**: Open-Meteo is keyless; zero credentials stored.
- **HTTPS enforced**: GitHub Pages enforces TLS 1.2+ automatically.
- **Content Security Policy**: Configured via `<meta>` tag in `index.html`. Restricts:
  - `default-src 'self'` — all resources default to same origin
  - `style-src` — allows Google Fonts stylesheets + inline styles (`'unsafe-inline'`)
  - `font-src` — allows Google Fonts CDN
  - `connect-src` — allows Open-Meteo API endpoints only
  - `img-src` — same-origin + `data:` URIs
  - `script-src` — same-origin + inline scripts (`'unsafe-inline'`)
  - `manifest-src` — same-origin
  - Validated in CI via `Check Content-Security-Policy` step
- **Dependency updates**: Automated via Dependabot (Actions runners only).

## Tooling

- **`.editorconfig`**: Consistent editor settings (2-space indent, UTF-8, LF line endings)

## Runbook

### Manual deploy
Push to `main` — GitHub Actions handles the rest.
```bash
git push origin main
```

### Rollback
1. Go to **Actions** → **Deploy to GitHub Pages** → select previous successful run
2. Click **Re-run all jobs**
3. Deployment uses the git state from that run's commit.

### Force re-deploy
```bash
gh workflow run "Deploy to GitHub Pages" --repo Dmitrii-Nefedov/supercat
```

---

*Maintained by DevOps — last updated 2026-07-05 (Run 14)
