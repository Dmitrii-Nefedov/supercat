import json
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from weather import (
    day_name,
    wind_direction,
    color_temp,
    search_city,
    fetch_weather,
    api_get,
    WMO_ICONS,
    WMO_DESC,
    City,
)


SAMPLE_CITY = City("Moscow", "Russia", 55.7558, 37.6173, "Europe/Moscow")


def make_mock_response(data: dict, status: int = 200):
    m = MagicMock()
    m.__enter__.return_value = m
    m.read.return_value = json.dumps(data).encode()
    m.status = status
    return m


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


class TestWindDirection:
    def test_north(self):
        assert wind_direction(0) == "С"

    def test_north_northeast(self):
        assert wind_direction(22.5) == "ССВ"

    def test_northeast(self):
        assert wind_direction(45) == "СВ"

    def test_east(self):
        assert wind_direction(90) == "В"

    def test_south(self):
        assert wind_direction(180) == "Ю"

    def test_west(self):
        assert wind_direction(270) == "З"

    def test_northwest(self):
        assert wind_direction(315) == "СЗ"

    def test_none(self):
        assert wind_direction(None) == "—"


class TestColorTemp:
    def test_hot_above_30(self):
        result = color_temp(35)
        assert "\033[31m" in result
        assert "35" in result

    def test_warm_20_to_29(self):
        result = color_temp(25)
        assert "\033[33m" in result
        assert "25" in result

    def test_mild_10_to_19(self):
        result = color_temp(15)
        assert "\033[32m" in result
        assert "15" in result

    def test_cold_below_10(self):
        result = color_temp(5)
        assert "\033[36m" in result
        assert "5" in result

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


class TestApiGet:
    @patch("weather.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        expected = {"test": "data"}
        mock_urlopen.return_value = make_mock_response(expected)
        result = api_get("https://api.example.com", {"key": "val"})
        assert result == expected

    @patch("weather.urllib.request.urlopen")
    def test_timeout(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        with pytest.raises(urllib.error.URLError):
            api_get("https://api.example.com", {})


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
        assert cities[0].latitude == 55.7558
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
        assert result["current"]["weather_code"] == 0


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
