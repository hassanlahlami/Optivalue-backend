"""Attach Open-Meteo weather to scheduled matches (context shown in the report / API)."""
from __future__ import annotations
from sources.stadiums import coords_for
from sources.weather_openmeteo import weather_summary
from storage.repositories import MatchRepo


def update_weather(conn, client, date: str) -> int:
    """Look up weather for each match on `date` whose home stadium we know; store a summary."""
    repo = MatchRepo(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT match_id, home FROM matches WHERE substr(kickoff_utc,1,10)=?", (date,))]
    n = 0
    for r in rows:
        coords = coords_for(r["home"])
        if not coords:
            continue
        w = client.daily_weather(coords[0], coords[1], date)
        if not w:
            continue
        repo.set_weather(r["match_id"], weather_summary(w))
        n += 1
    return n
