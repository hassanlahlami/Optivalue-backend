"""Understat xG client — match-level expected goals (the free xG source the APIs don't give us).

Understat embeds match data in a page JS variable: `var datesData = JSON.parse('[...]')`. There is
no formal API, so this scrapes that JSON. It is gray-area ToS: used here for PERSONAL, rate-limited,
cached research only, and gated on robots.txt via scrape_base. Returns the columns the
xg_dixon_coles model needs: Date, HomeTeam, AwayTeam, FTHG, FTAG, HxG, AxG.

Configure a league with `history_source: understat` to fit the goals model on real xG.
(Note: Understat has no corners, so corner markets fall back / disable for such a league.)
"""
from __future__ import annotations
import json
import logging
import re
import pandas as pd
from .base import BaseResultsClient
from .scrape_base import polite_get

log = logging.getLogger(__name__)
URL = "https://understat.com/league/{league}/{season}"
# our football-data history_code -> Understat league slug
LEAGUE_SLUGS = {"E0": "EPL", "SP1": "La_liga", "D1": "Bundesliga", "I1": "Serie_A", "F1": "Ligue_1"}
# Understat full names -> The Odds API spelling (extend as needed).
TEAM_ALIASES = {
    "Manchester City": "Man City", "Manchester United": "Man United",
    "Newcastle United": "Newcastle", "Wolverhampton Wanderers": "Wolves",
    "Tottenham": "Tottenham", "West Ham": "West Ham", "Nottingham Forest": "Nott'm Forest",
}

_DATES_RE = re.compile(r"datesData\s*=\s*JSON\.parse\('([^']+)'\)")


def parse_understat(html: str) -> pd.DataFrame:
    """Extract finished matches with xG from an Understat league page's datesData blob."""
    m = _DATES_RE.search(html)
    if not m:
        return pd.DataFrame()
    data = json.loads(m.group(1).encode("utf-8").decode("unicode_escape"))
    rows = []
    for d in data:
        if not d.get("isResult"):
            continue
        try:
            rows.append({
                "Date": d["datetime"][:10],
                "HomeTeam": TEAM_ALIASES.get(d["h"]["title"], d["h"]["title"]),
                "AwayTeam": TEAM_ALIASES.get(d["a"]["title"], d["a"]["title"]),
                "FTHG": int(d["goals"]["h"]),
                "FTAG": int(d["goals"]["a"]),
                "HxG": float(d["xG"]["h"]),
                "AxG": float(d["xG"]["a"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return pd.DataFrame(rows)


class UnderstatClient(BaseResultsClient):
    def __init__(self, cache_dir: str, season: str = "2024", ttl: int = 86400) -> None:
        self.cache_dir = cache_dir
        self.season = season
        self.ttl = ttl

    def fetch_history(self, history_code: str) -> pd.DataFrame:
        league = LEAGUE_SLUGS.get(history_code, history_code)
        url = URL.format(league=league, season=self.season)
        try:
            html = polite_get(url, self.cache_dir, self.ttl)
        except Exception as exc:  # noqa: BLE001 - robots/network/parse: log and degrade gracefully
            log.error("Understat fetch failed for %s: %s", league, exc)
            return pd.DataFrame()
        return parse_understat(html)
