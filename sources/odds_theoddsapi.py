"""The Odds API client. Free tier: 500 req/month. Docs: https://the-odds-api.com/

Each league key is queried separately (the API is per-sport). Markets requested:
h2h and totals (goals). Corner totals are not offered by most books on the free tier;
when present under a 'totals_corners'-style key they are normalized too.
"""
from __future__ import annotations
import logging
from .base import BaseOddsClient, MatchOdds
from .sample import _normalize_match  # shared normalization
from .cache import cached_get

log = logging.getLogger(__name__)
BASE = "https://api.the-odds-api.com/v4/sports/{sport}/odds"

class TheOddsAPIClient(BaseOddsClient):
    def __init__(self, api_key: str, cache_dir: str, ttl: int,
                 markets: list[str], min_interval: float = 1.5) -> None:
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.markets = markets
        self.min_interval = min_interval

    def _api_markets(self) -> str:
        m = []
        if "h2h" in self.markets:
            m.append("h2h")
        if "totals_goals" in self.markets:
            m.append("totals")
        if "btts" in self.markets:
            m.append("btts")
        return ",".join(m) or "h2h"

    def fetch_odds(self, league_keys: list[str]) -> list[MatchOdds]:
        out: list[MatchOdds] = []
        for sport in league_keys:
            url = BASE.format(sport=sport)
            params = {"apiKey": self.api_key, "regions": "uk,eu",
                      "markets": self._api_markets(), "oddsFormat": "decimal"}
            try:
                data = cached_get(url, params, self.cache_dir, self.ttl, self.min_interval)
            except Exception as exc:  # noqa: BLE001 - log and continue other leagues
                log.error("odds fetch failed for %s: %s", sport, exc)
                continue
            for m in data:
                out.extend(_normalize_match(m))
        return out
