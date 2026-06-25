"""Open-Meteo weather client — a free, key-less API (no scraping needed).

Returns daily max temperature, precipitation, and wind for a venue + date. Uses the archive API
for past dates and the forecast API for today/future. Cached + rate-limited via sources.cache.
Weather affects scoring (wind/rain dampen passing, push long-ball play and corners), so it is a
useful future model covariate; for now it is attached to matches as context.
"""
from __future__ import annotations
import datetime as dt
import logging
from .cache import cached_get

log = logging.getLogger(__name__)
FORECAST = "https://api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
_DAILY = "temperature_2m_max,precipitation_sum,windspeed_10m_max"


def parse_open_meteo(payload: dict) -> dict | None:
    daily = (payload or {}).get("daily") or {}
    temps = daily.get("temperature_2m_max") or []
    if not temps:
        return None
    return {
        "temp_c": float(temps[0]),
        "precip_mm": float((daily.get("precipitation_sum") or [0.0])[0]),
        "wind_kmh": float((daily.get("windspeed_10m_max") or [0.0])[0]),
    }


def weather_summary(w: dict) -> str:
    return f"{w['temp_c']:.0f}°C, {w['precip_mm']:.1f}mm rain, {w['wind_kmh']:.0f}km/h wind"


class OpenMeteoClient:
    def __init__(self, cache_dir: str, ttl: int = 21600) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl

    def daily_weather(self, lat: float, lon: float, date: str) -> dict | None:
        base = ARCHIVE if date < dt.date.today().isoformat() else FORECAST
        params = {"latitude": lat, "longitude": lon, "daily": _DAILY,
                  "start_date": date, "end_date": date, "timezone": "UTC"}
        try:
            data = cached_get(base, params, self.cache_dir, self.ttl, min_interval=1.0)
        except Exception as exc:  # noqa: BLE001 - weather is best-effort context
            log.warning("Open-Meteo fetch failed (%s,%s,%s): %s", lat, lon, date, exc)
            return None
        return parse_open_meteo(data)
