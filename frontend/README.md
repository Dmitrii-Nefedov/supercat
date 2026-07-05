# Frontend Role

## Contributions

### Run 7 — Service Worker Upgrade (Offline API Cache)

**Problem**: The service worker only cached static assets (HTML, manifest). Weather API responses from Open-Meteo were fetched live with no offline fallback. If the user lost connectivity, previously loaded weather data was gone.

**Solution**: Upgraded the service worker (`sw.js`) with a dual-cache strategy:

- **`supercat-weather-v4`** — static asset cache (unchanged): install-time precache for `index.html`, `manifest.json`, `404.html`. Cache-first with network update for same-origin resources.
- **`supercat-api-v1`** — API response cache: network-first with Cache storage fallback for both `api.open-meteo.com` and `geocoding-api.open-meteo.com`. When offline, the SW serves the last successful API response, allowing the UI to render stale-but-useful weather data.

**Key decisions**:
- Network-first for APIs ensures fresh data when online but graceful degradation when offline
- Separate cache namespace prevents API bloat from evicting static assets
- Old caches (`v3` and earlier) are pruned on activate
- Error JSON fallback when both network and cache miss

**Files changed**:
- `sw.js` — full rewrite of fetch handler with dual-cache strategy

### Run 10 — CSS Extraction (Separate Stylesheet)

**Problem**: All 1226 lines of CSS were embedded in a `<style>` block inside `index.html`, making the HTML file ~2064 lines long. This hurt maintainability, prevented independent caching, and made the CSS harder to edit with tooling.

**Solution**: Extracted all CSS into a dedicated `frontend/styles.css` file and linked it from `index.html`.

**Key decisions**:
- CSS lives in `frontend/styles.css` under the existing `frontend/` directory, keeping the project flat
- No CSS changes were made — exact extraction preserves every rule, keyframe, and media query
- Service worker cache bumped to `v5` and `frontend/styles.css` added to precache list
- The 404 page keeps its own inline styles (standalone page, unrelated)
- JS remains inline in `index.html` — tightly coupled to the DOM structure; extraction would require a refactor

**Files changed**:
- `frontend/styles.css` — new file (1226 lines, all CSS from index.html)
- `index.html` — replaced 1226-line `<style>` block with `<link rel="stylesheet" href="frontend/styles.css">`
- `sw.js` — bumped cache to v5, added `frontend/styles.css` to STATIC_ASSETS

**Verification**:
- 37/37 JS tests pass
- `manifest.json` validates
- All 18 `@keyframes`, 3 `@media` blocks preserved
