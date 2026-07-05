"""Tests for supercat weather CLI."""

from __future__ import annotations

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from weather import (
    City,
    CityNotFoundError,
    ApiError,
    MAX_RETRIES,
    VERSION,
    WMO_DESC,
    WMO_ICONS,
    _uv_bar,
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
    print_hourly,
    resolve_city,
    search_city,
    wind_direction,
)

from weather import _build_wx_params

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
            "uv_index_max": [6.5, 4.0, 2.0],
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


# --- UV bar ---


class TestUvBar:
    def test_low_0(self):
        result = _uv_bar(0)
        assert "\033[36m" in result
        assert "UV 0.0" in result

    def test_low_2(self):
        result = _uv_bar(2)
        assert "\033[36m" in result
        assert "UV 2.0" in result

    def test_moderate_3(self):
        result = _uv_bar(3)
        assert "\033[32m" in result

    def test_moderate_5(self):
        result = _uv_bar(5)
        assert "\033[32m" in result

    def test_high_6(self):
        result = _uv_bar(6)
        assert "\033[33m" in result

    def test_high_7(self):
        result = _uv_bar(7)
        assert "\033[33m" in result

    def test_very_high_8(self):
        result = _uv_bar(8)
        assert "\033[31m" in result

    def test_very_high_10(self):
        result = _uv_bar(10)
        assert "\033[31m" in result

    def test_extreme_11(self):
        result = _uv_bar(11)
        assert "\033[35m" in result

    def test_extreme_above(self):
        result = _uv_bar(15)
        assert "\033[35m" in result

    def test_bar_length_max(self):
        result = _uv_bar(10)
        assert "\u2588" * 10 in result

    def test_bar_length_min(self):
        result = _uv_bar(0)
        assert "\u2591" * 10 in result

    def test_bar_rounded(self):
        result = _uv_bar(3.3)
        assert "UV 3.3" in result


# --- format_temp ---


def test_format_temp():
    assert format_temp(22.5) == "22\u00b0C"
    assert format_temp(0) == "0\u00b0C"
    assert format_temp(-5.7) == "-6\u00b0C"


# --- API get ---


class TestIsRetryableStatus:
    def test_5xx_is_retryable(self):
        from weather import _is_retryable_status
        for code in (500, 502, 503, 504):
            assert _is_retryable_status(code)

    def test_4xx_is_not_retryable(self):
        from weather import _is_retryable_status
        for code in (400, 401, 403, 404, 429):
            assert not _is_retryable_status(code)

    def test_2xx_is_not_retryable(self):
        from weather import _is_retryable_status
        assert not _is_retryable_status(200)
        assert not _is_retryable_status(304)


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

    @patch("weather.time.sleep")
    @patch("weather.urllib.request.urlopen")
    def test_retries_on_5xx(self, mock_urlopen, mock_sleep):
        import urllib.error
        err = urllib.error.HTTPError("https://api.example.com", 502, "Bad Gateway", {}, None)
        mock_urlopen.side_effect = err
        with pytest.raises(ApiError, match="HTTP 502"):
            api_get("https://api.example.com", {})
        assert mock_urlopen.call_count == MAX_RETRIES

    @patch("weather.time.sleep")
    @patch("weather.urllib.request.urlopen")
    def test_fails_fast_on_4xx(self, mock_urlopen, mock_sleep):
        import urllib.error
        err = urllib.error.HTTPError("https://api.example.com", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = err
        with pytest.raises(ApiError, match="HTTP 404"):
            api_get("https://api.example.com", {})
        assert mock_urlopen.call_count == 1

    @patch("weather.time.sleep")
    @patch("weather.urllib.request.urlopen")
    def test_retry_then_succeeds(self, mock_urlopen, mock_sleep):
        import urllib.error
        err = urllib.error.HTTPError("https://api.example.com", 503, "Service Unavailable", {}, None)
        success = make_mock_response({"status": "ok"})
        mock_urlopen.side_effect = [err, err, success]
        result = api_get("https://api.example.com", {})
        assert result == {"status": "ok"}
        assert mock_urlopen.call_count == 3


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
        assert obj[0]["uv_index_max"] == 6.5
        assert obj[1]["uv_index_max"] == 4.0
        assert obj[2]["uv_index_max"] == 2.0

    def test_format_hourly_json(self, sample_hourly_response):
        obj = format_hourly_json(sample_hourly_response)
        assert len(obj) == 6
        assert obj[0]["time"] == "2026-07-05T00:00"
        assert obj[0]["temperature"] == 20.0

    def test_format_current_no_daily(self, mock_city):
        data = {"current": {"temperature_2m": 22.5, "relative_humidity_2m": 55,
                            "apparent_temperature": 20.0, "weather_code": 2,
                            "wind_speed_10m": 12.0, "cloud_cover": 40}}
        obj = format_current_json(data, mock_city)
        assert obj["temperature"] == 22.5
        assert "sunrise" not in obj
        assert "forecast" not in obj

    def test_format_current_no_sunrise_sunset(self, mock_city):
        data = {"current": {"temperature_2m": 22.5, "relative_humidity_2m": 55,
                            "apparent_temperature": 20.0, "weather_code": 2,
                            "wind_speed_10m": 12.0, "cloud_cover": 40},
                "daily": {"time": [], "sunrise": [], "sunset": []}}
        obj = format_current_json(data, mock_city)
        assert "sunrise" not in obj

    def test_format_current_missing_optionals(self, mock_city):
        data = {"current": {"temperature_2m": 22.5, "relative_humidity_2m": 55,
                            "apparent_temperature": 20.0, "weather_code": 2,
                            "wind_speed_10m": 12.0, "cloud_cover": 40}}
        obj = format_current_json(data, mock_city)
        assert obj["wind_gusts"] is None
        assert obj["wind_direction"] is None
        assert obj["pressure"] is None
        assert obj["uv_index"] is None

    def test_format_forecast_missing_optionals(self):
        data = {"daily": {
            "time": ["2026-07-05"],
            "weather_code": [0],
            "temperature_2m_max": [25.0],
            "temperature_2m_min": [15.0],
        }}
        obj = format_forecast_json(data)
        assert obj[0]["precipitation_probability_max"] is None
        assert obj[0]["uv_index_max"] is None

    def test_format_hourly_missing_wind_direction(self, sample_hourly_response):
        data = dict(sample_hourly_response)
        del data["hourly"]["wind_direction_10m"]
        obj = format_hourly_json(data)
        assert obj[0]["wind_direction"] is None


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


# --- cmd_search output ---


class TestCmdSearch:
    def test_cmd_search_shows_results(self):
        from weather import cmd_search
        cities = [
            City("Moscow", "Russia", 55.7558, 37.6173, "Europe/Moscow"),
            City("Moscow", "USA", 46.7320, -117.0000, "America/Los_Angeles"),
        ]
        with patch("weather.search_city", return_value=cities):
            with patch("sys.stdout", new_callable=StringIO) as buf:
                args = argparse.Namespace(query="Moscow", format="text")
                cmd_search(args)
                output = buf.getvalue()
                assert "Moscow" in output
                assert "Russia" in output
                assert "USA" in output
                assert "55.76" in output

    def test_cmd_search_no_results(self):
        from weather import cmd_search
        with patch("weather.search_city", return_value=[]):
            with patch("sys.stdout", new_callable=StringIO) as buf:
                args = argparse.Namespace(query="Xyzzy", format="text")
                cmd_search(args)
                output = buf.getvalue()
                assert "No results" in output or "Xyzzy" in output


# --- print_current output ---


class TestPrintCurrent:
    SAMPLE_DATA = {
        "current": {
            "temperature_2m": 22.5,
            "apparent_temperature": 20.1,
            "relative_humidity_2m": 55,
            "weather_code": 0,
            "wind_speed_10m": 12.3,
            "wind_gusts_10m": 18.5,
            "wind_direction_10m": 180,
            "cloud_cover": 30,
            "surface_pressure": 1013.2,
            "uv_index": 4.2,
        },
        "daily": {
            "sunrise": ["2026-07-05T05:30:00"],
            "sunset": ["2026-07-05T21:15:00"],
        },
    }

    def test_prints_city_name(self):
        from weather import print_current
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(self.SAMPLE_DATA, SAMPLE_CITY)
            output = buf.getvalue()
            assert "Moscow" in output
            assert "Russia" in output

    def test_prints_temperature(self):
        from weather import print_current
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(self.SAMPLE_DATA, SAMPLE_CITY)
            output = buf.getvalue()
            assert "22" in output
            assert "°C" in output

    def test_prints_humidity(self):
        from weather import print_current
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(self.SAMPLE_DATA, SAMPLE_CITY)
            output = buf.getvalue()
            assert "55%" in output

    def test_prints_sunrise_sunset(self):
        from weather import print_current
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(self.SAMPLE_DATA, SAMPLE_CITY)
            output = buf.getvalue()
            assert "05:30" in output
            assert "21:15" in output

    def test_prints_wind_gusts(self):
        from weather import print_current
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(self.SAMPLE_DATA, SAMPLE_CITY)
            output = buf.getvalue()
            assert "gusts" in output
            assert "18" in output

    def test_no_sunrise_sunset_when_missing(self):
        from weather import print_current
        data = dict(self.SAMPLE_DATA)
        data["daily"] = {}
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(data, SAMPLE_CITY)
            output = buf.getvalue()
            assert "Sunrise" not in output
            assert "Sunset" not in output

    def test_no_pressure_when_missing(self):
        from weather import print_current
        data = dict(self.SAMPLE_DATA)
        del data["current"]["surface_pressure"]
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(data, SAMPLE_CITY)
            output = buf.getvalue()
            assert "Pressure" not in output

    def test_no_gusts_when_missing(self):
        from weather import print_current
        data = dict(self.SAMPLE_DATA)
        data["current"] = dict(data["current"])
        del data["current"]["wind_gusts_10m"]
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_current(data, SAMPLE_CITY)
            output = buf.getvalue()
            assert "gusts" not in output


# --- print_forecast output ---


class TestPrintForecast:
    SAMPLE_FORECAST = {
        "daily": {
            "time": ["2026-07-05", "2026-07-06", "2026-07-07", "2026-07-08",
                     "2026-07-09", "2026-07-10", "2026-07-11"],
            "weather_code": [0, 1, 2, 3, 45, 61, 95],
            "temperature_2m_max": [28, 25, 22, 20, 18, 15, 12],
            "temperature_2m_min": [18, 16, 14, 12, 10, 8, 6],
            "precipitation_probability_max": [10, 20, 30, 40, 50, 60, 70],
            "uv_index_max": [1.5, 3.0, 5.5, 7.0, 9.0, 11.0, 0.5],
        }
    }

    def test_prints_forecast_title(self):
        from weather import print_forecast
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(self.SAMPLE_FORECAST)
            output = buf.getvalue()
            assert "7-Day Forecast" in output

    def test_prints_all_days(self):
        from weather import print_forecast
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(self.SAMPLE_FORECAST)
            output = buf.getvalue()
            assert "Today" in output
            assert "Tomorrow" in output

    def test_prints_temperatures(self):
        from weather import print_forecast
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(self.SAMPLE_FORECAST)
            output = buf.getvalue()
            assert "28" in output
            assert "12" in output

    def test_prints_precipitation(self):
        from weather import print_forecast
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(self.SAMPLE_FORECAST)
            output = buf.getvalue()
            assert "10%" in output
            assert "70%" in output

    def test_no_precip_when_missing(self):
        from weather import print_forecast
        data = {"daily": {
            "time": ["2026-07-05"],
            "weather_code": [0],
            "temperature_2m_max": [25],
            "temperature_2m_min": [15],
        }}
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(data)
            output = buf.getvalue()
            assert "💧" not in output

    def test_prints_uv_index(self):
        from weather import print_forecast
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(self.SAMPLE_FORECAST)
            output = buf.getvalue()
            assert "UV" in output
            assert "1.5" in output
            assert "11.0" in output

    def test_no_uv_when_missing(self):
        from weather import print_forecast
        data = {"daily": {
            "time": ["2026-07-05"],
            "weather_code": [0],
            "temperature_2m_max": [25],
            "temperature_2m_min": [15],
        }}
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_forecast(data)
            output = buf.getvalue()
            assert "UV" not in output


# --- cmd_current dispatch ---


class TestCmdCurrent:
    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_cmd_current_calls_print(self, mock_fetch, mock_resolve):
        mock_resolve.return_value = SAMPLE_CITY
        mock_fetch.return_value = {"current": {"temperature_2m": 22.5, "weather_code": 0}}
        with patch("weather.print_current") as mock_print:
            args = argparse.Namespace(city="Moscow", format="text")
            cmd_current(args)
            mock_fetch.assert_called_once_with(SAMPLE_CITY)
            mock_print.assert_called_once()

    @patch("weather.resolve_city")
    def test_cmd_current_city_not_found(self, mock_resolve):
        mock_resolve.side_effect = CityNotFoundError("City not found: Xyzzy")
        with patch("sys.stderr", new_callable=StringIO) as buf:
            with pytest.raises(SystemExit):
                args = argparse.Namespace(city="Xyzzy", format="text")
                cmd_current(args)
            assert "City not found" in buf.getvalue()


# --- cmd_forecast dispatch ---


class TestCmdForecast:
    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_cmd_forecast_calls_print(self, mock_fetch, mock_resolve):
        mock_resolve.return_value = SAMPLE_CITY
        mock_fetch.return_value = {"current": {}, "daily": {}}
        with patch("weather.print_current") as mock_print_cur:
            with patch("weather.print_forecast") as mock_print_fc:
                args = argparse.Namespace(city="Moscow", format="text")
                cmd_forecast(args)
                mock_fetch.assert_called_once_with(SAMPLE_CITY)
                mock_print_cur.assert_called_once()
                mock_print_fc.assert_called_once()

    @patch("weather.resolve_city")
    def test_cmd_forecast_city_not_found(self, mock_resolve):
        mock_resolve.side_effect = CityNotFoundError("City not found: Xyzzy")
        with patch("sys.stderr", new_callable=StringIO) as buf:
            with pytest.raises(SystemExit):
                args = argparse.Namespace(city="Xyzzy", format="text")
                cmd_forecast(args)
            assert "City not found" in buf.getvalue()


# --- main() edge cases ---


class TestMainEdgeCases:
    def test_main_invalid_command(self):
        from weather import main
        with patch.object(sys, "argv", ["weather.py", "invalid_cmd"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_no_args(self):
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


# --- _build_wx_params ---


class TestBuildWxParams:
    def test_default_params(self, mock_city):
        params = _build_wx_params(mock_city)
        assert params["latitude"] == 55.7558
        assert params["longitude"] == 37.6173
        assert "current" in params
        assert "daily" in params
        assert params["timezone"] == "Europe/Moscow"
        assert params["forecast_days"] == 7
        assert "hourly" not in params

    def test_hourly_mode(self, mock_city):
        params = _build_wx_params(mock_city, hourly=True)
        assert params["forecast_hours"] == 48
        assert params["forecast_days"] == 1

    def test_hourly_fields(self, mock_city):
        params = _build_wx_params(mock_city, hourly=True)
        hourly_fields = params["hourly"]
        assert "temperature_2m" in hourly_fields
        assert "precipitation" in hourly_fields
        assert "weather_code" in hourly_fields
        assert "wind_speed_10m" in hourly_fields
        assert "wind_direction_10m" in hourly_fields

    def test_uv_index_in_current(self, mock_city):
        params = _build_wx_params(mock_city)
        assert "uv_index" in params["current"]

    def test_uv_index_max_in_daily(self, mock_city):
        params = _build_wx_params(mock_city)
        assert "uv_index_max" in params["daily"]


# --- print_hourly output ---


class TestPrintHourly:
    SAMPLE = {
        "hourly": {
            "time": [f"2026-07-05T{h:02d}:00" for h in range(12)],
            "temperature_2m": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                               26.0, 27.0, 28.0, 29.0, 30.0, 31.0],
            "precipitation": [0.5, 0.0, 0.0, 0.0, 1.2, 0.0,
                              0.0, 0.0, 0.0, 0.3, 0.0, 0.0],
            "weather_code": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
            "wind_speed_10m": [5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                               11.0, 12.0, 13.0, 14.0, 15.0, 16.0],
            "wind_direction_10m": [0.0, 45.0, 90.0, 135.0, 180.0, 225.0,
                                   270.0, 315.0, 360.0, 22.5, 67.5, 112.5],
        }
    }

    def test_title_includes_city(self):
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(self.SAMPLE, SAMPLE_CITY)
            output = buf.getvalue()
            assert "Moscow" in output
            assert "48-Hour Forecast" in output

    def test_time_labels(self):
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(self.SAMPLE, SAMPLE_CITY)
            output = buf.getvalue()
            assert "00:00" in output
            assert "03:00" in output
            assert "06:00" in output

    def test_temperatures(self):
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(self.SAMPLE, SAMPLE_CITY)
            output = buf.getvalue()
            assert "20" in output
            assert "23" in output
            assert "26" in output

    def test_nonzero_precip_shown(self):
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(self.SAMPLE, SAMPLE_CITY)
            output = buf.getvalue()
            assert "0.5" in output
            assert "mm" in output or "㎜" in output

    def test_zero_precip_skipped(self):
        sample = {
            "hourly": {
                "time": ["2026-07-05T00:00", "2026-07-05T03:00", "2026-07-05T06:00"],
                "temperature_2m": [20.0, 21.0, 22.0],
                "precipitation": [0.0, 0.0, 0.0],
                "weather_code": [0, 0, 0],
                "wind_speed_10m": [5.0, 6.0, 7.0],
                "wind_direction_10m": [0.0, 45.0, 90.0],
            }
        }
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(sample, SAMPLE_CITY)
            output = buf.getvalue()
            assert "0.0mm" not in output

    def test_wind_speed(self):
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(self.SAMPLE, SAMPLE_CITY)
            output = buf.getvalue()
            assert "5km/h" in output or "5 km/h" in output or "5.0" in output

    def test_wind_direction(self):
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(self.SAMPLE, SAMPLE_CITY)
            output = buf.getvalue()
            assert "\u0421" in output

    def test_missing_direction_graceful(self):
        sample = {
            "hourly": {
                "time": ["2026-07-05T00:00", "2026-07-05T03:00", "2026-07-05T06:00"],
                "temperature_2m": [20.0, 21.0, 22.0],
                "precipitation": [0.0, 0.0, 0.0],
                "weather_code": [0, 0, 0],
                "wind_speed_10m": [5.0, 6.0, 7.0],
            }
        }
        with patch("sys.stdout", new_callable=StringIO) as buf:
            print_hourly(sample, SAMPLE_CITY)
            output = buf.getvalue()
            assert "km/h" in output


# --- cmd_hourly dispatch ---


class TestCmdHourly:
    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_text_dispatch(self, mock_fetch, mock_resolve):
        mock_resolve.return_value = SAMPLE_CITY
        mock_fetch.return_value = {"current": {}, "hourly": {"time": []}}
        with patch("weather.print_current") as mock_print_cur:
            with patch("weather.print_hourly") as mock_print_hr:
                args = argparse.Namespace(city="Moscow", format="text")
                cmd_hourly(args)
                mock_fetch.assert_called_once_with(SAMPLE_CITY, hourly=True)
                mock_print_cur.assert_called_once()
                mock_print_hr.assert_called_once()

    @patch("weather.resolve_city")
    @patch("weather.fetch_weather")
    def test_json_output(self, mock_fetch, mock_resolve, sample_hourly_response):
        mock_resolve.return_value = SAMPLE_CITY
        mock_fetch.return_value = sample_hourly_response
        with patch("sys.stdout", new_callable=StringIO) as buf:
            args = argparse.Namespace(city="Moscow", format="json")
            cmd_hourly(args)
            output = buf.getvalue()
            parsed = json.loads(output)
            assert "hourly" in parsed
            assert "location" in parsed
            assert parsed["location"]["name"] == "Moscow"

    @patch("weather.resolve_city")
    def test_city_not_found(self, mock_resolve):
        mock_resolve.side_effect = CityNotFoundError("City not found: Xyzzy")
        with patch("sys.stderr", new_callable=StringIO) as buf:
            with pytest.raises(SystemExit):
                args = argparse.Namespace(city="Xyzzy", format="text")
                cmd_hourly(args)
            assert "City not found" in buf.getvalue()


# --- main() ApiError handling ---


class TestMainApiError:
    def test_main_catches_api_error_from_current(self):
        from weather import main
        with patch("weather.cmd_current", side_effect=ApiError("HTTP 500: timeout")):
            with patch.object(sys, "argv", ["weather.py", "now", "Moscow"]):
                with patch("sys.stderr", new_callable=StringIO) as buf:
                    with pytest.raises(SystemExit):
                        main()
                    assert "API Error" in buf.getvalue()

    def test_main_catches_api_error_from_forecast(self):
        from weather import main
        with patch("weather.cmd_forecast", side_effect=ApiError("HTTP 500: timeout")):
            with patch.object(sys, "argv", ["weather.py", "forecast", "Moscow"]):
                with patch("sys.stderr", new_callable=StringIO) as buf:
                    with pytest.raises(SystemExit):
                        main()
                    assert "API Error" in buf.getvalue()

    def test_main_catches_api_error_from_hourly(self):
        from weather import main
        with patch("weather.cmd_hourly", side_effect=ApiError("HTTP 500: timeout")):
            with patch.object(sys, "argv", ["weather.py", "hourly", "Moscow"]):
                with patch("sys.stderr", new_callable=StringIO) as buf:
                    with pytest.raises(SystemExit):
                        main()
                    assert "API Error" in buf.getvalue()

    def test_main_catches_api_error_from_search(self):
        from weather import main
        with patch("weather.cmd_search", side_effect=ApiError("HTTP 500: timeout")):
            with patch.object(sys, "argv", ["weather.py", "search", "Moscow"]):
                with patch("sys.stderr", new_callable=StringIO) as buf:
                    with pytest.raises(SystemExit):
                        main()
                    assert "API Error" in buf.getvalue()
