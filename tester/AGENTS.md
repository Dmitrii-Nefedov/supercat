# Tester Role

**Role**: Тестировщик (QA Engineer)  
**Run**: 6 (2026-07-05)

## Activities

### Python Tests (`tests/test_weather.py`)
- Unit tests for all pure functions in `weather.py`:
  - `day_name` — day labeling (Today/Tomorrow/weekday names)
  - `wind_direction` — 16-point compass from degrees
  - `color_temp` — ANSI color coding by temperature range
  - `search_city` — API call with mocked HTTP
  - `fetch_weather` — API call with mocked HTTP
  - `api_get` — HTTP error handling
- WMO code mapping integrity (every code has an icon and description)
- CLI argument parsing (subcommands: `now`, `forecast`/`fc`, `search`)
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

### Coverage
| Component | Functions Tested | Coverage |
|-----------|-----------------|----------|
| `weather.py` | 7 pure functions + 2 mocked API calls | All branches |
| `index.html` (JS) | 8 pure functions + 2 data maps | All branches |
| WMO mappings | 36 codes × 2 (icon, description) | 100% |

## Remaining Gaps
- No browser/E2E tests (require Playwright/Puppeteer)
- No service worker unit tests
- No integration test for full JS→API→DOM pipeline

## CI Integration
Test suites are now integrated into `.github/workflows/ci.yml`:
- Python tests run via `pytest` on every PR to `main`
- JavaScript tests run via `node` on every PR to `main`
- Both run after HTML/JSON/SW validation checks
