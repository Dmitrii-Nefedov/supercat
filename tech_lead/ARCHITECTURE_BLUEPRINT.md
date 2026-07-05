# Architecture Blueprint: Phase 3

> Tech Lead: @supercat-agent | Updated: 2026-07-05 (Run 9)

## Current State Assessment

### What Exists
- **Single-file SPA** (`index.html`, 2064 lines — HTML + CSS + JS inline)
- **Python CLI** (`weather.py`)
- **PWA** (`sw.js` + `manifest.json`)
- **Tests** (`tests/test_weather.py` — 60 tests, `tests/test_weather.js` — 37 tests)
- **CI/CD** (`.github/workflows/ci.yml` + `deploy.yml`)
- **Role docs**: `analyst/`, `tech_lead/`, `devops/`, `tester/`, `designer/`, `frontend/`, `backend_dev/`

### Phase 2 Completed Items ✅
| Task | Status | Commit |
|------|--------|--------|
| Precipitation bar wiring | ✅ Done | `be041c7` |
| Wind compass | ✅ Done | `be041c7` |
| Search "not found" state | ✅ Done | `be041c7` |
| Scroll fade mask | ✅ Done | `be041c7` |
| View transitions | ✅ Done | `be041c7` |
| Refresh button animation | ✅ Done | `be041c7` |
| Weather alerts integration | ✅ Done | `fa5f682` |
| Python CLI refactor (hourly, JSON, errors) | ✅ Done | `474af64` |
| SW offline API cache | ✅ Done | `c23480e` |
| CI test runners (pytest + node) | ✅ Done | `f342c84` |

### What Remains
1. **CSS extraction to `styles.css`** — P1, highest-impact structural improvement. index.html at 2064 lines remains monolithic.
2. **SVG weather icons** — P2, emoji rendering varies by OS.
3. **Deploy workflow fix** — ✅ Fixed this run: `enablement: true` added to `configure-pages` step.
4. **SW cache bug** — ✅ Fixed this run: `catch` now prefers `cached` over `404.html`.
5. **CI pipeline** — Both CI and Deploy workflows were failing. Deploy now fixed; CI needs investigation.

### Analyst-Identified Gaps (from `analyst/PHASE2_ANALYSIS.md`)
- **WMO code drift** — same mapping data in 5 locations, no shared source of truth
- **Render/Integration tests** — zero tests for `renderWeather()`, DOM, or SW behavior
- **PNG app icons** — SVG emoji icons fail on iOS; need 192x192 and 512x512 PNG
- **No CSP headers** — no XSS mitigation
- **`.highlighted` dead CSS class** — defined but never used
- **Placeholder contrast** — fails WCAG AA (3.7:1)
- **SW scope not set** — missing `scope` in manifest

---

## Blueprint: Phase 3 Goals

### Priority Matrix

| Priority | Task | Effort | Impact | Dependencies |
|----------|------|--------|--------|--------------|
| P0 | Fix CI pipeline (investigate test failures) | 1-2h | Critical | None |
| P1 | Extract CSS to `styles.css` | 2-3h | Very High | None |
| P1 | Add PNG app icons (192x192, 512x512) | 1h | High | None |
| P2 | Add CSP meta tag | 30min | Medium | None |
| P2 | Animated SVG weather icons | 6-8h | Medium | CSS extraction (P1) |
| P2 | WMO code deduplication (shared JSON) | 2-3h | Medium | None |
| P3 | Add render tests (Playwright/jsdom) | 4-6h | Medium | CSS extraction (P1) |
| P3 | Fix placeholder contrast | 15min | Low | None |
| P3 | Remove `.highlighted` dead code | 5min | Low | None |
| P3 | Set SW scope in manifest | 5min | Low | None |

---

## Execution Plan

### Phase 3.1 — Infrastructure Fixes (sequential)

#### Task A: Fix CI pipeline
- **Agent**: devops
- **Changes**:
  1. Investigate CI failures — test the workflows locally
  2. Ensure `ci.yml` runs pytest and node tests correctly
  3. Fix any test regressions
- **Artifact**: Modified CI workflow + test fixes
- **Verification**: CI passes on push

#### Task B: Add deploy enablement (✅ Done this run)
- **Status**: Fixed. `actions/configure-pages@v5` now uses `enablement: true`.

### Phase 3.2 — Structural (can parallelize)

#### Task C: Extract CSS to `styles.css`
- **Agent**: frontend_dev
- **Changes**:
  1. Extract all `<style>` block content to `styles.css`
  2. Replace inline `<style>` with `<link rel="stylesheet" href="styles.css">`
  3. Update `sw.js` cache list to include `styles.css`
  4. Increment cache version to v5
- **Artifact**: New `styles.css` + modified `index.html`, `sw.js`
- **Verification**: Visual diff before/after; app loads identically

#### Task D: Add PNG app icons
- **Agent**: designer
- **Changes**:
  1. Create 192x192 and 512x512 PNG icons (weather-themed)
  2. Update `manifest.json` to reference PNG icons alongside SVG
  3. Add preload links in `<head>`
- **Artifact**: `icon-192.png`, `icon-512.png`, modified `manifest.json`, `index.html`
- **Verification**: Lighthouse PWA audit passes icon checks

#### Task E: Add CSP meta tag
- **Agent**: frontend_dev
- **Changes**: Add `<meta http-equiv="Content-Security-Policy">` with:
  - `default-src 'self'`
  - `style-src 'self' https://fonts.googleapis.com 'unsafe-inline'`
  - `font-src 'self' https://fonts.gstatic.com`
  - `img-src 'self' data:`
  - `connect-src 'self' https://api.open-meteo.com https://geocoding-api.open-meteo.com`
  - `frame-ancestors 'none'`
- **Artifact**: Modified `index.html`
- **Verification**: Browser console shows no CSP violations

### Phase 3.3 — Enhancement (post-refactor)

#### Task F: SVG weather icons
- **Agent**: designer
- **Dependencies**: Task C (CSS extraction reduces inline complexity)
- **Changes**:
  1. Create inline SVG sprites for 7+ weather conditions
  2. Replace emoji in WMO code map with SVG references
  3. Add CSS animation classes for each SVG icon
- **Artifact**: Modified `index.html` — WMO map + SVG definitions + CSS
- **Verification**: Visual check across weather conditions; Lighthouse a11y check

#### Task G: WMO code deduplication
- **Agent**: backend_dev
- **Changes**:
  1. Create `wmo-codes.json` as shared source of truth
  2. Update `weather.py` to import from JSON
  3. Update `tests/test_weather.py` to import from JSON
  4. Update `tests/test_weather.js` to import from JSON
  5. Update `index.html` to fetch or inline the JSON
- **Artifact**: New `wmo-codes.json`, modified `weather.py`, `index.html`, tests
- **Verification**: All existing tests still pass

### Phase 3.4 — Test Quality (ongoing)

#### Task H: Add render tests
- **Agent**: tester
- **Dependencies**: Task C (CSS extraction)
- **Changes**:
  1. Set up Playwright or jsdom test environment
  2. Write tests for `renderWeather()`, `renderError()`, `renderLoader()`
  3. Add SW integration test
- **Artifact**: New test files
- **Verification**: Tests pass in CI

---

## Architectural Decisions

### ADR-4: CSS Extraction (carried forward from Phase 2)
- **Decision**: Single `styles.css` file — no CSS modules, no build step
- **Updated Risk**: Low. Extraction is mechanical. Service worker cache must be updated.

### ADR-5: PNG Icon Approach
- **Decision**: Generate simple weather-themed SVGs rasterized to PNG (or use data-URI fallback)
- **Rationale**: iOS requires actual PNG files for homescreen icons. Data-URI SVG works on Android but fails iOS.
- **Risk**: Low. Only affects PWA install flow.

### ADR-6: WMO Code Single Source of Truth
- **Decision**: External `wmo-codes.json` file loaded by both Python and JS
- **Rationale**: Eliminates drift between 5 locations. Test coverage ensures completeness.
- **Risk**: Medium. Requires careful import strategy for `index.html` (fetch vs inline). Prefer inline in JS at build-free no-compromise: add a script tag with the JSON as a JS constant.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CI still fails after fixes | Medium | High | Investigate root cause before merging; add local test pass verification |
| CSS extraction breaks SW cache | Low | High | Update cache version and static assets list |
| SVG icons increase HTML size | Low | Low | Inline SVG definitions add ~10-15KB; acceptable for PWA |
| WMO deduplication breaks imports | Medium | Medium | Test all 5 locations after change; CI must run both test suites |

---

## Success Criteria

1. All CI workflows pass (CI + Deploy)
2. CSS extracted to `styles.css` with identical visual output
3. PNG icons available and manifest references them
4. SW cache v5 includes all new assets
5. No file exceeds 800 lines
6. All existing tests pass (no regressions)

---

## Recommended Agent Assignments

| Task | Primary Agent | Review By |
|------|--------------|-----------|
| CI pipeline fix | devops | tech_lead |
| CSS extraction | frontend_dev | tech_lead |
| PNG app icons | designer | frontend_dev |
| CSP meta tag | frontend_dev | security |
| SVG icons | designer | frontend_dev |
| WMO deduplication | backend_dev | tester |
| Render tests | tester | frontend_dev |
