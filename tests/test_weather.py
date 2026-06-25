from sources.weather_openmeteo import parse_open_meteo, weather_summary
from sources.stadiums import coords_for

PAYLOAD = {"daily": {"time": ["2026-06-25"], "temperature_2m_max": [21.3],
                     "precipitation_sum": [0.0], "windspeed_10m_max": [18.2]}}


def test_parse_open_meteo_extracts_fields():
    w = parse_open_meteo(PAYLOAD)
    assert w["temp_c"] == 21.3
    assert w["precip_mm"] == 0.0
    assert w["wind_kmh"] == 18.2


def test_parse_open_meteo_empty_payload():
    assert parse_open_meteo({}) is None


def test_weather_summary_readable():
    s = weather_summary({"temp_c": 21.3, "precip_mm": 0.0, "wind_kmh": 18.2})
    assert "21" in s and "km/h" in s


def test_coords_known_and_national_team_absent():
    assert coords_for("Arsenal") is not None
    assert coords_for("Argentina") is None  # national teams have no fixed stadium
