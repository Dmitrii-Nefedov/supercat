# Supercat Weather 🌤️

A beautiful, feature-rich weather forecast web app powered by [Open-Meteo](https://open-meteo.com) (free API, no key required).

## Features

- **Current weather**: temperature, feels-like, humidity, wind, cloud cover, atmospheric pressure
- **7-day forecast**: daily highs/lows with WMO weather icons and precipitation probability
- **24-hour forecast**: toggle between daily and hourly views with horizontal scroll
- **Sunrise & sunset**: displayed in the details panel
- **Dynamic backgrounds**: animated CSS gradients and particle effects matching the weather (rain, snow, sunny, cloudy, foggy, thunderstorm, night)
- **City search**: autocomplete search with debounce via Open-Meteo Geocoding API
- **Geolocation**: one-click weather at your current location
- **PWA**: installable on mobile (manifest + service worker with offline cache)
- **Responsive**: works on desktop and mobile
- **Russian UI**: интерфейс на русском языке

## Usage

### Web App

Open `index.html` in a browser, or deploy to any static hosting.

### Python CLI

```bash
# Search for a city
./weather.py search "Moscow"

# Current weather
./weather.py now "Moscow"

# Current weather + 7-day forecast
./weather.py forecast "Moscow"
./weather.py fc "Moscow"
```

Requires Python 3.10+ and network access to `api.open-meteo.com`.

## Deployment

### GitHub Pages

The app is fully static and ready for GitHub Pages:

1. Go to **Settings → Pages → Source** and select **GitHub Actions**
2. Push `.github/workflows/deploy.yml` to `main`
3. The app will be available at `https://<user>.github.io/supercat/`

Or manually: **Settings → Pages → Source → `main` branch → `/` (root)**.

## Tech Stack

- Vanilla HTML/CSS/JS — no framework, no build step
- [Open-Meteo API](https://open-meteo.com) — weather data and geocoding
- CSS `backdrop-filter` glassmorphism, CSS gradients and keyframe animations
- PWA — `manifest.json` + service worker
- Python 3 — CLI companion tool

## API References

| API | Endpoint |
|-----|----------|
| Weather Forecast | `https://api.open-meteo.com/v1/forecast` |
| Geocoding | `https://geocoding-api.open-meteo.com/v1/search` |

## License

MIT
