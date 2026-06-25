"""National-team results client for international competitions (e.g. World Cup).

Source: the free, maintained martj42/international_results dataset on GitHub, which
lists every senior men's international since 1872. No API key required.

CSV columns (source): date, home_team, away_team, home_score, away_score, tournament,
city, country, neutral. We rename to the model's format (Date, HomeTeam, AwayTeam,
FTHG, FTAG) and keep only recent seasons for relevance.

# NAIVE: There are NO corner counts for international matches in any free dataset, so the
# corners model cannot be fit for the international model_group — corner markets are
# auto-disabled for the World Cup. Also note many World Cup fixtures are at NEUTRAL venues,
# but the goals model applies a single global home-advantage term to whichever side the
# odds feed labels "home"; treat international home advantage as approximate and improve
# here (venue-aware gamma) first.
"""
from __future__ import annotations
import io
import logging
import os
import time
import pandas as pd
import requests
from .base import BaseResultsClient

log = logging.getLogger(__name__)
DEFAULT_URL = ("https://raw.githubusercontent.com/martj42/international_results/"
               "master/results.csv")

# Map dataset team names to The Odds API spelling where they differ. Extend as needed;
# names that already match (most do) need no entry.
TEAM_ALIASES = {
    "United States": "USA",
    "South Korea": "Korea Republic",
    "IR Iran": "Iran",
    "Ivory Coast": "Cote d'Ivoire",
}


class InternationalResultsClient(BaseResultsClient):
    def __init__(self, cache_dir: str, since_year: int = 2018,
                 ttl: int = 86400, url: str = DEFAULT_URL, min_interval: float = 1.0) -> None:
        self.cache_dir = cache_dir
        self.since_year = since_year
        self.ttl = ttl
        self.url = url
        self.min_interval = min_interval

    def fetch_history(self, history_code: str) -> pd.DataFrame:
        # history_code is ignored — there is a single international results file. The cache
        # honours the spec's "cache API responses in source clients" requirement.
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, "international_results.csv")
        if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < self.ttl:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        else:
            resp = requests.get(self.url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)

        df = pd.read_csv(io.StringIO(text))
        df = df.rename(columns={"date": "Date", "home_team": "HomeTeam",
                                "away_team": "AwayTeam", "home_score": "FTHG",
                                "away_score": "FTAG"})
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        # Keep recent matches only (string compare works on YYYY-MM-DD ISO dates).
        df = df[df["Date"] >= f"{self.since_year}-01-01"]
        for col in ("HomeTeam", "AwayTeam"):
            df[col] = df[col].replace(TEAM_ALIASES)
        # Keep the `neutral` flag (most World Cup games) so the venue-aware model can use it.
        cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]
        if "neutral" in df.columns:
            cols.append("neutral")
        return df[cols].reset_index(drop=True)
