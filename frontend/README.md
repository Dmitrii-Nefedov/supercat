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
