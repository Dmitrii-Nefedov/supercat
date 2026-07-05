#!/usr/bin/env python3
"""Supercat Weather — terminal weather forecast from Open-Meteo."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


GEO_API = "https://geocoding-api.open-meteo.com/v1/search"
WX_API = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "supercat-weather/2.0"
MAX_RETRIES = 3
RETRY_DELAY = 1.0
VERSION = "2.0.0"

WMO_ICONS: dict[int, str] = {
    0: "\U00002600", 1: "\U0001f324", 2: "\U000026c5", 3: "\U00002601",
    45: "\U0001f32b", 48: "\U0001f32b",
    51: "\U0001f326", 53: "\U0001f326", 55: "\U0001f326",
    56: "\U0001f327", 57: "\U0001f327",
    61: "\U0001f327", 63: "\U0001f327", 65: "\U0001f327",
    66: "\U0001f327", 67: "\U0001f327",
    71: "\U0001f328", 73: "\U0001f328", 75: "\U0001f328", 77: "\U0001f328",
    80: "\U0001f326", 81: "\U0001f326", 82: "\U0001f326",
    85: "\U0001f328", 86: "\U0001f328",
    95: "\u26c8", 96: "\u26c8", 99: "\u26c8",
}

WMO_DESC: dict[int, str] = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Heavy freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Rain showers", 81: "Heavy rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"
EMDASH = "\u2014"
HLINE = "\u2500"


class WeatherError(Exception):
    """Base exception for weather CLI errors."""


class CityNotFoundError(WeatherError):
    """Raised when a city search returns no results."""


class ApiError(WeatherError):
    """Raised when the weather API returns an error."""


@dataclass
class City:
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


def api_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise ApiError(f"HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
    raise ApiError(f"Request failed after {MAX_RETRIES} retries: {last_error}") from last_error


def search_city(query: str) -> list[City]:
    data = api_get(GEO_API, {"name": query, "count": 8, "language": "en", "format": "json"})
    results = data.get("results") or []
    return [
        City(
            name=r["name"],
            country=r.get("country", ""),
            latitude=r["latitude"],
            longitude=r["longitude"],
            timezone=r.get("timezone", "UTC"),
        )
        for r in results
    ]


def resolve_city(name: str) -> City:
    cities = search_city(name)
    if not cities:
        raise CityNotFoundError(f"City not found: {name}")
    return cities[0]


def _build_wx_params(city: City, hourly: bool = False) -> dict[str, Any]:
    params: dict[str, Any] = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,surface_pressure,uv_index",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,precipitation_probability_max,uv_index_max",
        "timezone": city.timezone,
        "forecast_days": 1 if hourly else 7,
    }
    if hourly:
        params["hourly"] = "temperature_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        params["forecast_hours"] = 48
    return params


def fetch_weather(city: City, hourly: bool = False) -> dict[str, Any]:
    return api_get(WX_API, _build_wx_params(city, hourly=hourly))


def day_name(date_str: str, index: int) -> str:
    if index == 0:
        return "Today"
    if index == 1:
        return "Tomorrow"
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%a")


def wind_direction(degrees: float | None) -> str:
    if degrees is None:
        return EMDASH
    dirs = ["\u0421", "\u0421\u0421\u0412", "\u0421\u0412", "\u0412\u0421\u0412",
            "\u0412", "\u0412\u042e\u0412", "\u042e\u0412", "\u042e\u042e\u0412",
            "\u042e", "\u042e\u042e\u0417", "\u042e\u0417", "\u0417\u042e\u0417",
            "\u0417", "\u0417\u0421\u0417", "\u0421\u0417", "\u0421\u0421\u0417"]
    return dirs[round(degrees / 22.5) % 16]


def color_temp(temp: float) -> str:
    if temp >= 30:
        return f"{RED}{temp:.0f}{RESET}"
    elif temp >= 20:
        return f"{YELLOW}{temp:.0f}{RESET}"
    elif temp >= 10:
        return f"{GREEN}{temp:.0f}{RESET}"
    else:
        return f"{CYAN}{temp:.0f}{RESET}"


def format_temp(temp: float) -> str:
    return f"{temp:.0f}\u00b0C"


def _uv_bar(uv: float) -> str:
    if uv >= 11:
        color = MAGENTA
    elif uv >= 8:
        color = RED
    elif uv >= 6:
        color = YELLOW
    elif uv >= 3:
        color = GREEN
    else:
        color = CYAN
    filled = min(round(uv), 10)
    bar = "\u2588" * filled + "\u2591" * (10 - filled)
    return f"{color}UV {uv:.1f} {bar}{RESET}"


def format_current_json(data: dict[str, Any], city: City) -> dict[str, Any]:
    cur = data["current"]
    result: dict[str, Any] = {
        "location": {"name": city.name, "country": city.country, "timezone": city.timezone},
        "temperature": cur["temperature_2m"],
        "feels_like": cur["apparent_temperature"],
        "humidity": cur["relative_humidity_2m"],
        "weather_code": cur["weather_code"],
        "weather_description": WMO_DESC.get(cur["weather_code"], "Unknown"),
        "wind_speed": cur["wind_speed_10m"],
        "wind_gusts": cur.get("wind_gusts_10m"),
        "wind_direction": cur.get("wind_direction_10m"),
        "cloud_cover": cur["cloud_cover"],
        "pressure": cur.get("surface_pressure"),
        "uv_index": cur.get("uv_index"),
    }
    if "daily" in data:
        daily = data["daily"]
        if daily.get("sunrise") and daily.get("sunset"):
            result["sunrise"] = daily["sunrise"][0]
            result["sunset"] = daily["sunset"][0]
    return result


def print_current(data: dict[str, Any], city: City) -> None:
    cur = data["current"]
    code = cur["weather_code"]
    icon = WMO_ICONS.get(code, "\U0001f324")
    desc = WMO_DESC.get(code, "Unknown")
    temp = cur["temperature_2m"]
    feels = cur["apparent_temperature"]
    humid = cur["relative_humidity_2m"]
    wind = cur["wind_speed_10m"]
    gusts = cur.get("wind_gusts_10m")
    wind_dir = cur.get("wind_direction_10m")
    cloud = cur["cloud_cover"]
    pressure = cur.get("surface_pressure")
    uv = cur.get("uv_index")

    location = f"{city.name}, {city.country}" if city.country else city.name
    header = f"{BOLD}{icon}  {location}{RESET}"
    print(f"\n  {header}")
    print(f"  {DIM}{'=' * 40}{RESET}")
    print(f"  {color_temp(temp)}\u00b0C   {desc}")
    print(f"  {DIM}Feels like{RESET} {color_temp(feels)}\u00b0C   {DIM}UV{RESET} {uv if uv is not None else EMDASH}")
    gust_str = f"  gusts {gusts:.0f} km/h" if gusts is not None else ""
    dir_str = f" {wind_direction(wind_dir)}" if wind_dir is not None else ""
    print(f"  {DIM}Humidity{RESET}    {humid}%   {DIM}Wind{RESET}  {wind:.0f} km/h{gust_str}{dir_str}   {DIM}Clouds{RESET}  {cloud}%")
    if pressure is not None:
        print(f"  {DIM}Pressure{RESET}   {pressure:.0f} hPa")

    if "daily" in data:
        daily = data["daily"]
        if daily.get("sunrise") and daily.get("sunset"):
            sunrise = daily["sunrise"][0][11:16]
            sunset = daily["sunset"][0][11:16]
            print(f"  {DIM}Sunrise{RESET}   {sunrise}   {DIM}Sunset{RESET}  {sunset}")
    print()


def print_forecast(data: dict[str, Any]) -> None:
    daily = data["daily"]
    print(f"  {BOLD}7-Day Forecast{RESET}")
    print(f"  {DIM}{HLINE * 40}{RESET}")

    for i in range(len(daily["time"])):
        name = day_name(daily["time"][i], i)
        icon = WMO_ICONS.get(daily["weather_code"][i], "\U0001f324")
        high = daily["temperature_2m_max"][i]
        low = daily["temperature_2m_min"][i]
        precip = daily.get("precipitation_probability_max", [None] * 7)[i]
        precip_str = f"  {DIM}\U0001f4a7{RESET}{precip:.0f}%" if precip is not None else ""
        uv = daily.get("uv_index_max", [None] * 7)[i]
        uv_str = f"  {_uv_bar(uv)}" if uv is not None else ""
        print(f"  {icon}  {name:<10}  {color_temp(high)}\u00b0 /{color_temp(low)}\u00b0{precip_str}{uv_str}")

    print()


def format_forecast_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    daily = data["daily"]
    days: list[dict[str, Any]] = []
    for i in range(len(daily["time"])):
        days.append({
            "date": daily["time"][i],
            "weather_code": daily["weather_code"][i],
            "temperature_max": daily["temperature_2m_max"][i],
            "temperature_min": daily["temperature_2m_min"][i],
            "precipitation_probability_max": daily.get("precipitation_probability_max", [None] * 7)[i],
            "uv_index_max": daily.get("uv_index_max", [None] * 7)[i],
        })
    return days


def print_hourly(data: dict[str, Any], city: City) -> None:
    hourly = data["hourly"]
    times = hourly["time"]
    print(f"\n  {BOLD}48-Hour Forecast \u2014 {city.name}{RESET}")
    print(f"  {DIM}{HLINE * 40}{RESET}")
    for i in range(0, len(times), 3):
        t = times[i]
        icon = WMO_ICONS.get(hourly["weather_code"][i], "\U0001f324")
        temp = hourly["temperature_2m"][i]
        precip = hourly["precipitation"][i]
        wind = hourly["wind_speed_10m"][i]
        wdir = hourly.get("wind_direction_10m", [None] * len(times))[i]
        time_label = t[11:16]
        precip_str = f" {precip:.1f}mm" if precip and precip > 0 else ""
        dir_str = f" {wind_direction(wdir)}" if wdir is not None else ""
        print(f"  {icon}  {time_label}  {color_temp(temp)}\u00b0{precip_str}  {DIM}{wind:.0f}km/h{DIM}{dir_str}{RESET}")
    print()


def format_hourly_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    hourly = data["hourly"]
    hours: list[dict[str, Any]] = []
    for i in range(len(hourly["time"])):
        hours.append({
            "time": hourly["time"][i],
            "temperature": hourly["temperature_2m"][i],
            "precipitation": hourly["precipitation"][i],
            "weather_code": hourly["weather_code"][i],
            "wind_speed": hourly["wind_speed_10m"][i],
            "wind_direction": hourly.get("wind_direction_10m", [None] * len(hourly["time"]))[i],
        })
    return hours


def cmd_current(args: argparse.Namespace) -> None:
    try:
        city = resolve_city(args.city)
    except CityNotFoundError as e:
        print(f"{RED}{e}{RESET}", file=sys.stderr)
        sys.exit(1)
    data = fetch_weather(city)
    if args.format == "json":
        obj = format_current_json(data, city)
        if "daily" in data:
            obj["forecast"] = format_forecast_json(data)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return
    print_current(data, city)


def cmd_forecast(args: argparse.Namespace) -> None:
    try:
        city = resolve_city(args.city)
    except CityNotFoundError as e:
        print(f"{RED}{e}{RESET}", file=sys.stderr)
        sys.exit(1)
    data = fetch_weather(city)
    if args.format == "json":
        obj = format_current_json(data, city)
        obj["forecast"] = format_forecast_json(data)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return
    print_current(data, city)
    print_forecast(data)


def cmd_hourly(args: argparse.Namespace) -> None:
    try:
        city = resolve_city(args.city)
    except CityNotFoundError as e:
        print(f"{RED}{e}{RESET}", file=sys.stderr)
        sys.exit(1)
    data = fetch_weather(city, hourly=True)
    if args.format == "json":
        obj = format_current_json(data, city)
        obj["hourly"] = format_hourly_json(data)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return
    print_current(data, city)
    print_hourly(data, city)


def cmd_search(args: argparse.Namespace) -> None:
    cities = search_city(args.query)
    if args.format == "json":
        print(json.dumps([asdict(c) for c in cities], indent=2, ensure_ascii=False))
        return
    if not cities:
        print(f"{DIM}No results for '{args.query}'{RESET}")
        return
    print(f"\n  {BOLD}Results for '{args.query}':{RESET}")
    for c in cities:
        region = f", {c.country}" if c.country else ""
        print(f"  \U0001f4cd {c.name}{region}  {DIM}({c.latitude:.2f}, {c.longitude:.2f}){RESET}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="weather.py",
        description="Supercat Weather — terminal weather from Open-Meteo",
    )
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_now = sub.add_parser("now", help="Show current weather")
    p_now.add_argument("city", help="City name")

    p_forecast = sub.add_parser("forecast", aliases=["fc"], help="Show current weather + 7-day forecast")
    p_forecast.add_argument("city", help="City name")

    p_hourly = sub.add_parser("hourly", aliases=["hr"], help="Show 48-hour forecast")
    p_hourly.add_argument("city", help="City name")

    p_search = sub.add_parser("search", help="Search for a city")
    p_search.add_argument("query", help="City name to search")

    args = parser.parse_args()

    try:
        if args.command == "now":
            cmd_current(args)
        elif args.command in ("forecast", "fc"):
            cmd_forecast(args)
        elif args.command in ("hourly", "hr"):
            cmd_hourly(args)
        elif args.command == "search":
            cmd_search(args)
    except ApiError as e:
        print(f"{RED}API Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)
    except WeatherError as e:
        print(f"{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
