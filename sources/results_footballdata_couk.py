"""football-data.co.uk historical CSV client. No API key required.

CSV columns used: Date, HomeTeam, AwayTeam, FTHG, FTAG, HC, AC.
URL pattern: https://www.football-data.co.uk/mmz4281/{season}/{code}.csv
e.g. season '2425' code 'E0' = Premier League 2024/25.
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
URL = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
# Base result columns plus Pinnacle taken (PS*) and closing (PSC*) odds, kept when present
# so the CLV/ROI backtest can measure edge against real historical prices.
COLS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HC", "AC",
        "PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA"]

class FootballDataCoUkClient(BaseResultsClient):
    def __init__(self, cache_dir: str, season: str = "2425",
                 ttl: int = 86400, min_interval: float = 1.0) -> None:
        self.cache_dir = cache_dir
        self.season = season
        self.ttl = ttl
        self.min_interval = min_interval

    def fetch_history(self, history_code: str) -> pd.DataFrame:
        url = URL.format(season=self.season, code=history_code)
        # On-disk CSV cache (spec mandates caching in source clients). History changes
        # at most once per match-day, so a long TTL avoids re-downloading every run.
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, f"fdcouk_{self.season}_{history_code}.csv")
        if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < self.ttl:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        else:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        df = pd.read_csv(io.StringIO(text))
        present = [c for c in COLS if c in df.columns]
        return df[present].dropna(subset=["HomeTeam", "AwayTeam"])
