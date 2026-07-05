# Tester Role

**Role**: Тестировщик (QA Engineer)  
**Run**: 14 (2026-07-05)

## Activities

### Python Tests (`tests/test_weather.py`)
- Unit tests for all functions in `weather.py`:
  - `day_name` — day labeling (Today/Tomorrow/weekday names)
  - `wind_direction` — 16-point compass from degrees
  - `color_temp` — ANSI color coding by temperature range
  - `format_temp` — temperature string formatting
  - `search_city` — API call with mocked HTTP
  - `resolve_city` — city resolution with error handling
  - `fetch_weather` — API call with mocked HTTP (supports hourly flag)
  - `api_get` — HTTP retry and error handling
  - `format_current_json`, `format_forecast_json`, `format_hourly_json` — JSON output helpers
  - `print_current` — output rendering for current weather (city, temp, humidity, gusts, sunrise/sunset, missing fields)
  - `print_forecast` — output rendering for 7-day forecast (title, all days, temps, precip, missing data)
  - `print_hourly` — output rendering for 48-hour forecast (title with city, time labels, temps, precip, wind, direction)
  - `_build_wx_params` — API parameter builder (default, hourly mode, fields, uv_index, uv_index_max)
  - `cmd_search` — search result display with multiple cities and empty results
  - `cmd_current`, `cmd_forecast` — dispatch chain from resolve→fetch→print; handles city-not-found
  - `cmd_hourly` — dispatch chain for hourly mode (text, JSON, city-not-found)
  - `main()` edge cases — invalid command, no-args, version flag, ApiError from all 4 subcommands
  - JSON format output for `now`, `forecast`, `hourly`, `search` commands
  - JSON edge cases — missing daily/sunrise/sunset, missing optionals, missing wind_direction
- WMO code mapping integrity (every code has an icon and description)
- CLI argument parsing (subcommands: `now`, `forecast`/`fc`, `hourly`/`hr`, `search`)
- Pytest fixtures for sample data (current response, hourly response, geo response)
- Usage: `python3 -m pytest tests/test_weather.py -v`

### JavaScript Tests (`tests/test_weather.js`)
- Unit tests for pure functions extracted from `index.html`:
  - `convertTemp` — °C ↔ °F conversion
  - `tempLabel` — unit label formatting
  - `getDayName` — day-of-week labeling (Russian)
  - `isDaytime` — sunrise/sunset comparison
  - `windDirection` — 16-point compass from degrees
  - `getUVClass` — UV index risk category CSS class
  - `setWeatherTheme` — WMO code → weather theme mapping
  - `formatTime` — ISO datetime → HH:MM extraction
  - WMO code → icon/description mapping consistency
- Framework: Node.js (no DOM, pure function testing)
- Usage: `node tests/test_weather.js`

### Service Worker Tests (`tests/test_sw.js`)
- Unit tests for `sw.js` lifecycle and fetch strategy using Node.js `vm` module:
  - **install event**: registers listeners, caches static assets (index.html, manifest.json, 404.html), calls skipWaiting
  - **activate event**: deletes old cache versions, preserves current cache (v3), calls clients.claim
  - **fetch event (navigate)**: returns network response on success, falls back to cached index.html on failure
  - **fetch event (non-navigate)**: returns cached content when available, fetches from network when not cached, falls back to 404.html on network failure
  - **cache strategy**: caches same-origin successful responses, does NOT cache cross-origin responses
- Uses `vm.runInContext` to evaluate `sw.js` in a mocked ServiceWorker environment
- Usage: `node tests/test_sw.js`

### Bug Fixed in Run 14
- **`format_hourly_json` IndexError**: `hourly.get("wind_direction_10m", [None])[i]` crashed when `wind_direction_10m` was missing and `i > 0`. Fixed to `hourly.get("wind_direction_10m", [None] * len(hourly["time"]))[i]` at `weather.py:315`.

### Coverage

| Component | Functions Tested | Tests | Coverage |
|-----------|-----------------|-------|----------|
| `weather.py` | 14 functions + 4 cmd fns + 3 json fns + 1 param builder + 1 output fn | 120 | All branches, output formatting, error paths, JSON output, JSON edge cases |
| `index.html` (JS) | 8 pure functions + 2 data maps | 37 | All branches |
| `sw.js` | 3 lifecycle events + fetch strategy | 22 | Install/activate/fetch paths, cache policy |
| WMO mappings | 28 codes × 2 (icon, desc) | 3 | 100% |

## Remaining Gaps
- No browser/E2E tests (require Playwright/Puppeteer)
- No integration test for full JS→API→DOM pipeline
- No accessibility (a11y) tests
- No performance/load tests
- 27 DOM-dependent JS functions in `index.html` untested (renderWeather, bindSearchUI, bindAlerts, fetchWeather async, renderHourly, renderError, renderLoader)
- `weather.py` tests mock external APIs — no integration test against real Open-Meteo

## CI Integration
All test suites run in `.github/workflows/ci.yml` on every PR/push to `main`:
- Python tests (120 tests via pytest)
- JavaScript tests (37 tests via node)
- Service worker tests (22 tests via node)
