# Architecture Blueprint: Phase 2

> Tech Lead: @supercat-agent | Date: 2026-07-05

## Current State Assessment

### What Exists
- **Single-file SPA** (`index.html`, 1673 lines — HTML + CSS + JS inline)
- **Python CLI** (`weather.py`, 239 lines)
- **PWA** (`sw.js` + `manifest.json`)
- **Tests** (`tests/test_weather.py` — 39 tests, `tests/test_weather.js` — 37 tests)
- **CI/CD** (`.github/workflows/ci.yml` + `deploy.yml`)
- **Role docs**: `analyst/`, `tech_lead/`, `devops/`, `tester/`

### What's Missing / Incomplete
1. **Designer folder** — was created but is absent from the working tree. Code changes from the designer (wind compass, scroll fade, not-found state, precip bar wiring, view transitions) are partially missing or incomplete.
2. **Precipitation bars** — CSS exists (`.precip-bar`, `.precip-bar-fill` at lines 659–673) but is **not wired** into `renderHourly()` JS template (line 1186).
3. **Wind compass** — Not implemented. Wind direction shows as text only.
4. **Search "not found" state** — Not implemented. No visual feedback when geocoding returns empty.
5. **Scroll fade (mask-image)** — Not implemented.
6. **Single-file bottleneck** — `index.html` at 1673 lines is fragile; no separation of concerns.
7. **Weather alerts** — Open-Meteo supports weather alerts API; not integrated.
8. **No SVG weather icons** — Emoji rendering varies by OS.

---

## Blueprint: Phase 2 Goals

### Priority Matrix

| Priority | Task | Effort | Impact | Dependencies |
|----------|------|--------|--------|--------------|
| P0 | Wire precipitation bars into hourly template | Minutes | High | None |
| P0 | Implement wind compass (rotating arrow) | Minutes | High | None |
| P0 | Add search "not found" state | Minutes | Medium | None |
| P1 | Extract CSS to separate file | 2-3h | Very High | None |
| P1 | Add scroll fade mask | 15min | Low | None |
| P2 | Weather alerts integration | 4-6h | Medium | CSS extraction |
| P2 | Animated SVG weather icons | 6-8h | Medium | CSS extraction |
| P3 | i18n framework (string externalization) | 4-6h | Medium | CSS extraction |
| P3 | Lighthouse CI audit | 1-2h | Medium | CI workflow |

---

## Execution Plan

### Phase 2.1 — Quick Wins (parallel, any role)

These tasks have zero dependencies and can be executed in parallel:

#### Task A: Wire precipitation bars into hourly forecast render
- **Agent**: frontend_dev or designer
- **Changes**: `renderHourly()` template — add `<div class="precip-bar"><div class="precip-bar-fill" style="width:X%"></div></div>` after the percentage text
- **Artifact**: Modified `index.html` line ~1190
- **Verification**: Visual check of hourly forecast

#### Task B: Implement wind compass
- **Agent**: designer
- **Changes**: 
  - Add compass arrow CSS (rotating indicator using `transform: rotate(deg)`)
  - Replace text-only wind direction display with an arrow + text label
  - Wire `wind_direction_10m` value directly to CSS rotation
- **Artifact**: Modified `index.html` — details section + new CSS
- **Verification**: Visual check

#### Task C: Add search not-found state
- **Agent**: designer or frontend_dev
- **Changes**: 
  - In `searchCities()` callback: when results array is empty, show "Городов не найдено" message
  - Add CSS for the empty state
- **Artifact**: Modified `index.html` — JS logic + CSS
- **Verification**: Search for gibberish string

#### Task D: Add hourly scroll fade mask
- **Agent**: designer
- **Changes**: Add `mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent)` to `.hourly-scroll`
- **Artifact**: Modified `index.html` CSS
- **Verification**: Visual check of scroll edges

### Phase 2.2 — Structural Improvement (sequential)

#### Task E: Extract CSS to separate file `styles.css`
- **Agent**: frontend_dev
- **Dependencies**: Phase 2.1 (to avoid merge conflicts with inline changes)
- **Changes**:
  1. Extract all `<style>` block content to `styles.css`
  2. Replace inline `<style>` with `<link rel="stylesheet" href="styles.css">`
  3. Update `sw.js` cache list to include `styles.css`
  4. Update `manifest.json` if needed
- **Artifact**: New `styles.css` + modified `index.html`, `sw.js`
- **Verification**: App loads and renders identically

#### Task F: Add `uv_index_max` to Python CLI daily params
- **Agent**: backend_dev
- **Dependencies**: None (can run in parallel with Phase 2.1)
- **Changes**: Add `uv_index_max` to the daily params in `weather.py` forecast command
- **Artifact**: Modified `weather.py`
- **Verification**: Python tests pass

### Phase 2.3 — Enhancement (sequential, post-refactor)

#### Task G: Weather alerts integration
- **Agent**: frontend_dev
- **Dependencies**: Task E (CSS extraction reduces inline complexity)
- **Changes**:
  1. Add `weather_alerts` parameter to Open-Meteo API call
  2. Parse alert data and render as banner/card above forecast
  3. CSS for alert states (warning, advisory, watch)
- **Artifact**: Modified `index.html`
- **Verification**: Test with known alert regions

#### Task H: SVG weather icons
- **Agent**: designer
- **Dependencies**: Task E (CSS extraction)
- **Changes**:
  1. Create inline SVG sprites for 7+ weather conditions
  2. Replace emoji in WMO code map with SVG references
  3. Add CSS animation classes for each SVG icon
- **Artifact**: Modified `index.html` — WMO map + SVG definitions + CSS
- **Verification**: Visual check across weather conditions

---

## Architectural Decisions for Phase 2

### ADR-1: CSS Extraction Strategy
- **Decision**: Extract to single `styles.css` file (not CSS modules or CSS-in-JS)
- **Rationale**: Zero build step, no new dependencies, backward-compatible with PWA caching
- **Risk**: Low. Pure refactor, no behavior change.

### ADR-2: Weather Alert Rendering
- **Decision**: Render alerts as a dismissible banner above the forecast toggle
- **Rationale**: Highest visibility without disrupting layout; matches native weather app patterns
- **Risk**: Medium. Alert API schema may vary by region. Add graceful fallback.

### ADR-3: SVG Icon Strategy
- **Decision**: Inline SVG definitions in the HTML (not external files)
- **Rationale**: Zero network requests; cache-friendly with service worker; easy to animate with CSS
- **Risk**: Low. Increases HTML size by ~10-15KB but eliminates emoji inconsistency.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Merge conflicts from parallel agent execution | High | Medium | Use sequential phases for structural changes; parallel only for isolated sections |
| CSS extraction breaks service worker cache | Low | High | Update sw.js cache list and increment cache version |
| Open-Meteo API schema changes | Low | Medium | Add schema validation in fetchWeather() |
| Designer changes lost again | Medium | High | Commit designer changes in a dedicated PR immediately |

---

## Success Criteria

1. All Phase 2.1 tasks completed and verified
2. CSS extracted to `styles.css` with identical visual output
3. All existing tests pass (no regressions)
4. Service worker cache v4 includes new assets
5. No file exceeds 800 lines (down from 1673)

---

## Recommended Agent Assignments

| Task | Primary Agent | Review By |
|------|--------------|-----------|
| Precipitation bar wiring | designer | tester |
| Wind compass | designer | tester |
| Not-found state | designer | tester |
| Scroll fade | designer | tester |
| CSS extraction | frontend_dev | tech_lead |
| Python CLI fix | backend_dev | tester |
| Weather alerts | frontend_dev | tech_lead |
| SVG icons | designer | frontend_dev |
