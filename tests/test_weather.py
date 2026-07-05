"""Tests for supercat weather CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from weather import (
    City,
    CityNotFoundError,
    ApiError,
    VERSION,
    WMO_DESC,
    WMO_ICONS,
    api_get,
    cmd_current,
    cmd_forecast,
    cmd_hourly,
    cmd_search,
    color_temp,
    day_name,
    fetch_weather,
    format_current_json,
    format_forecast_json,
    format_hourly_json,
    format_temp,
    resolve_city,
    search_city,
    wind_direction,
)

SAMPLE_CITY = City("Moscow", "Russia", 55.7558, 37.6173, "Europe/Moscow")


def make_mock_response(data: dict, status: int = 200):
    m = MagicMock()
    m.__enter__.return_value = m
    m.read.return_value = json.dumps(data).encode()
    m.status = status
    return m


# --- Fixtures ---


@pytest.fixture
def mock_city() -> City:
    return SAMPLE_CITY


@pytest.fixture
def sample_geo_response() -> dict:
    return {
        "results": [
            {
                "name": "Moscow",
                "country": "Russia",
                "latitude": 55.76,
                "longitude": 37.62,
                "timezone": "Europe/Moscow",
            }
        ]
    }


@pytest.fixture
def sample_current_response() -> dict:
    return {
        "current": {
            "temperature_2m": 22.5,
            "relative_humidity_2m": 55,
            "apparent_temperature": 20.0,
            "weather_code": 2,
            "wind_speed_10m": 12.0,
            "wind_direction_10m": 180.0,
            "wind_gusts_10m": 20.0,
            "cloud_cover": 40,
            "surface_pressure": 1013.0,
            "uv_index": 4.5,
        },
        "daily": {
            "time": ["2026-07-05", "2026-07-06", "2026-07-07"],
            "weather_code": [2, 3, 1],
            "temperature_2m_max": [25.0, 23.0, 20.0],
            "temperature_2m_min": [15.0, 14.0, 12.0],
            "sunrise": ["2026-07-05T04:56"],
            "sunset": ["2026-07-05T21:12"],
            "precipitation_probability_max": [10, 40, 5],
        },
    }


@pytest.fixture
def sample_hourly_response(sample_current_response: dict) -> dict:
    resp = dict(sample_current_response)
    resp["hourly"] = {
        "time": [f"2026-07-05T{h:02d}:00" for h in range(6)],
        "temperature_2m": [20.0, 21.0, 22.0, 23.0, 22.5, 21.0],
        "precipitation": [0.0, 0.0, 0.1, 0.5, 0.0, 0.0],
        "weather_code": [2, 2, 3, 3, 2, 2],
        "wind_speed_10m": [10.0, 11.0, 12.0, 13.0, 12.0, 11.0],
        "wind_direction_10m": [180.0, 190.0, 200.0, 210.0, 200.0, 190.0],
    }
    return resp


# --- Day name ---


class TestDayName:
    def test_today(self):
        assert day_name("2026-07-05", 0) == "Today"

    def test_tomorrow(self):
        assert day_name("2026-07-06", 1) == "Tomorrow"

    def test_monday(self):
        assert day_name("2026-07-06", 2) == "Mon"

    def test_tuesday(self):
        assert day_name("2026-07-07", 2) == "Tue"

    def test_wednesday(self):
        assert day_name("2026-07-08", 2) == "Wed"

    def test_thursday(self):
        assert day_name("2026-07-09", 2) == "Thu"

    def test_friday(self):
        assert day_name("2026-07-10", 2) == "Fri"

    def test_saturday(self):
        assert day_name("2026-07-11", 2) == "Sat"

    def test_sunday(self):
        assert day_name("2026-07-12", 2) == "Sun"


# --- Wind direction ---


class TestWindDirection:
    def test_north(self):
        assert wind_direction(0) == "\u0421"

    def test_north_northeast(self):
        assert wind_direction(22.5) == "\u0421\u0421\u0412"

    def test_northeast(self):
        assert wind_direction(45) == "\u0421\u0412"

    def test_east(self):
        assert wind_direction(90) == "\u0412"

    def test_south(self):
        assert wind_direction(180) == "\u042e"

    def test_west(self):
        assert wind_direction(270) == "\u0417"

    def test_northwest(self):
        assert wind_direction(315) == "\u0421\u0417"

    def test_none(self):
        assert wind_direction(None) == "\u2014"


# --- Temperature color ---


class TestColorTemp:
    def test_hot_above_30(self):
        result = color_temp(35)
        assert "\033[31m" in result

    def test_warm_20_to_29(self):
        result = color_temp(25)
        assert "\033[33m" in result

    def test_mild_10_to_19(self):
        result = color_temp(15)
        assert "\033[32m" in result

    def test_cold_below_10(self):
        result = color_temp(5)
        assert "\033[36m" in result

    def test_zero(self):
        result = color_temp(0)
        assert "\033[36m" in result

    def test_boundary_30(self):
        result = color_temp(30)
        assert "\033[31m" in result

    def test_boundary_20(self):
        result = color_temp(20)
        assert "\033[33m" in result

    def test_boundary_10(self):
        result = color_temp(10)
        assert "\033[32m" in result

    def test_negative(self):
        result = color_temp(-5)
        assert "\033[36m" in result


# --- format_temp ---


def test_format_temp():
    assert format_temp(22.5) == "22\u00b0C"
    assert format_temp(0) == "0\u00b0C"
    assert format_temp(-5.7) == "-6\u00b0C"


# --- API get ---


class TestApiGet:
    @patch("weather.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        expected = {"test": "data"}
        mock_urlopen.return_value = make_mock_response(expected)
        result = api_get("https://api.example.com", {"key": "val"})
        assert result == expected

    @patch("weather.time.sleep")
    @patch("weather.urllib.request.urlopen")
    def test_timeout(self, mock_urlopen, mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        with pytest.raises(ApiError, match="Request failed after 3 retries"):
            api_get("https://api.example.com", {})


# --- Search ---


class TestSearchCity:
    @patch("weather.api_get")
    def test_finds_cities(self, mock_api):
        mock_api.return_value = {
            "results": [
                {"name": "Moscow", "country": "Russia", "latitude": 55.7558,
                 "longitude": 37.6173, "timezone": "Europe/Moscow"},
            ]
        }
        cities = search_city("Moscow")
        assert len(cities) == 1
        assert cities[0].name == "Moscow"
        assert cities[0].country == "Russia"
        assert cities[0].timezone == "Europe/Moscow"

    @patch("weather.api_get")
    def test_no_results(self, mock_api):
        mock_api.return_value = {}
        cities = search_city("Xyzzy")
        assert cities == []

    @patch("weather.api_get")
    def test_multiple_results(self, mock_api):
        mock_api.return_value = {
            "results": [
                {"name": "London", "country": "United Kingdom",
                 "latitude": 51.5, "longitude": -0.1, "timezone": "Europe/London"},
                {"name": "London", "country": "Canada",
                 "latitude": 42.98, "longitude": -81.25, "timezone": "America/Toronto"},
            ]
        }
        cities = search_city("London")
        assert len(cities) == 2


# --- Resolve city ---


class TestResolveCity:
    @patch("weather.search_city")
    def test_found(self, mock_search):
        mock_search.return_value = [SAMPLE_CITY]
        result = resolve_city("Moscow")
        assert result == SAMPLE_CITY

    @patch("weather.search_city")
    def test_not_found(self, mock_search):
        mock_search.return_value = []
        with pytest.raises(CityNotFoundError):
            resolve_city("Nowhereville")


# --- Fetch weather ---


class TestFetchWeather:
    @patch("weather.api_get")
    def test_fetches_weather_data(self, mock_api):
        mock_data = {
            "current": {"temperature_2m": 22.5, "weather_code": 0},
            "daily": {"time": ["2026-07-05"]},
        }
        mock_api.return_value = mock_data
        result = fetch_weather(SAMPLE_CITY)
        assert result["current"]["temperature_2m"] == 22.5

    @patch("weather.api_get")
    def test_fetch_hourly(self, mock_api, mock_city):
        mock_api.return_value = {"current": {}, "daily": {}, "hourly": {}}
        result = fetch_weather(mock_city, hourly=True)
        assert "hourly" in result


# --- WMO mappings ---


class TestWmoMappings:
    def test_all_wmo_codes_have_icons(self):
        all_codes = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57,
                     61, 63, 65, 66, 67, 71, 73, 75, 77,
                     80, 81, 82, 85, 86, 95, 96, 99}
        for code in all_codes:
            assert code in WMO_ICONS, f"Missing WMO icon for code {code}"

    def test_all_wmo_codes_have_descriptions(self):
        all_codes = {0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57,
                     61, 63, 65, 66, 67, 71, 73, 75, 77,
                     80, 81, 82, 85, 86, 95, 96, 99}
        for code in all_codes:
            assert code in WMO_DESC, f"Missing WMO description for code {code}"

    def test_icon_count_matches_description_count(self):
        assert len(WMO_ICONS) == len(WMO_DESC)


# --- JSON format helpers ---


class TestJsonFormat:
    @patch("weather.api_get")
    def test_format_current_json(self, mock_api_get, sample_current_response, mock_city):
        mock_api_get.return_value = sample_current_response
        data = fetch_weather(mock_city)
        obj = format_current_json(data, mock_city)
        assert obj["temperature"] == 22.5
        assert obj["location"]["name"] == "Moscow"
        assert obj["sunrise"] == "2026-07-05T04:56"
        assert obj["weather_description"] == WMO_DESC[2]

    def test_format_forecast_json(self, sample_current_response):
        obj = format_forecast_json(sample_current_response)
        assert len(obj) == 3
        assert obj[0]["date"] == "2026-07-05"
        assert obj[0]["temperature_max"] == 25.0

    def test_format_hourly_json(self, sample_hourly_response):
        obj = format_hourly_json(sample_hourly_response)
        assert len(obj) == 6
        assert obj[0]["time"] == "2026-07-05T00:00"
        assert obj[0]["temperature"] == 20.0


# --- CLI commands ---


class TestCliCommands:
    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_cmd_current_json(self, mock_fetch, mock_resolve, mock_city, sample_current_response):
        mock_resolve.return_value = mock_city
        mock_fetch.return_value = sample_current_response
        ns = type("Args", (), {"city": "Moscow", "format": "json"})()
        cmd_current(ns)

    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_cmd_forecast_json(self, mock_fetch, mock_resolve, mock_city, sample_current_response):
        mock_resolve.return_value = mock_city
        mock_fetch.return_value = sample_current_response
        ns = type("Args", (), {"city": "Moscow", "format": "json"})()
        cmd_forecast(ns)

    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_cmd_hourly_json(self, mock_fetch, mock_resolve, mock_city, sample_hourly_response):
        mock_resolve.return_value = mock_city
        mock_fetch.return_value = sample_hourly_response
        ns = type("Args", (), {"city": "Moscow", "format": "json"})()
        cmd_hourly(ns)

    @patch("weather.search_city")
    def test_cmd_search_json(self, mock_search, mock_city):
        mock_search.return_value = [mock_city]
        ns = type("Args", (), {"query": "Moscow", "format": "json"})()
        cmd_search(ns)

    @patch("weather.resolve_city")
    def test_cmd_current_not_found(self, mock_resolve):
        mock_resolve.side_effect = CityNotFoundError("City not found: X")
        ns = type("Args", (), {"city": "X", "format": "text"})()
        with pytest.raises(SystemExit):
            cmd_current(ns)

    @patch("weather.resolve_city")
    def test_cmd_forecast_not_found(self, mock_resolve):
        mock_resolve.side_effect = CityNotFoundError("City not found: X")
        ns = type("Args", (), {"city": "X", "format": "text"})()
        with pytest.raises(SystemExit):
            cmd_forecast(ns)

    @patch("weather.resolve_city")
    def test_cmd_hourly_not_found(self, mock_resolve):
        mock_resolve.side_effect = CityNotFoundError("City not found: X")
        ns = type("Args", (), {"city": "X", "format": "text"})()
        with pytest.raises(SystemExit):
            cmd_hourly(ns)

    @patch("weather.search_city")
    def test_cmd_search_no_results(self, mock_search):
        mock_search.return_value = []
        ns = type("Args", (), {"query": "Xyzzy", "format": "text"})()
        cmd_search(ns)  # should not raise

    @patch("weather.search_city")
    def test_cmd_search_no_results_json(self, mock_search):
        mock_search.return_value = []
        ns = type("Args", (), {"query": "Xyzzy", "format": "json"})()
        cmd_search(ns)  # should not raise


# --- Version ---


class TestVersion:
    def test_version_defined(self):
        assert VERSION == "2.0.0"


# --- CLI arg parsing ---


class TestCliParsing:
    def test_now_command(self):
        from weather import main
        with patch("weather.cmd_current") as mock_cmd:
            with patch.object(sys, "argv", ["weather.py", "now", "Moscow"]):
                main()
            mock_cmd.assert_called_once()

    def test_forecast_command(self):
        from weather import main
        with patch("weather.cmd_forecast") as mock_cmd:
            with patch.object(sys, "argv", ["weather.py", "forecast", "Moscow"]):
                main()
            mock_cmd.assert_called_once()

    def test_fc_alias(self):
        from weather import main
        with patch("weather.cmd_forecast") as mock_cmd:
            with patch.object(sys, "argv", ["weather.py", "fc", "Moscow"]):
                main()
            mock_cmd.assert_called_once()

    def test_search_command(self):
        from weather import main
        with patch("weather.cmd_search") as mock_cmd:
            with patch.object(sys, "argv", ["weather.py", "search", "Moscow"]):
                main()
            mock_cmd.assert_called_once()

    def test_hourly_command(self):
        from weather import main
        with patch("weather.cmd_hourly") as mock_cmd:
            with patch.object(sys, "argv", ["weather.py", "hourly", "Moscow"]):
                main()
            mock_cmd.assert_called_once()

    def test_hr_alias(self):
        from weather import main
        with patch("weather.cmd_hourly") as mock_cmd:
            with patch.object(sys, "argv", ["weather.py", "hr", "Moscow"]):
                main()
            mock_cmd.assert_called_once()

    def test_no_args_exits(self):
        from weather import main
        with patch.object(sys, "argv", ["weather.py"]):
            with pytest.raises(SystemExit):
                main()

    def test_version_flag(self):
        from weather import main
        with patch.object(sys, "argv", ["weather.py", "--version"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
