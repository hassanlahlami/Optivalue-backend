"""Bundled-fixture source for --dry-run. Implements both client interfaces.

Reuses the same odds-normalization logic shape as the live Odds API client so the
pipeline sees identical MatchOdds records whether live or dry-run.
"""
from __future__ import annotations
import json
import os
import pandas as pd
from .base import BaseOddsClient, BaseResultsClient, MatchOdds

# Map The Odds API market keys to our internal market ids.
def _normalize_match(m: dict) -> list[MatchOdds]:
    out: list[MatchOdds] = []
    for bk in m.get("bookmakers", []):
        book = bk["key"]
        for market in bk.get("markets", []):
            mkey = market["key"]
            if mkey == "h2h":
                internal = "h2h"
            elif mkey == "totals":
                internal = "totals_goals"
            elif mkey == "totals_corners":
                internal = "totals_corners"
            else:
                continue
            for oc in market["outcomes"]:
                out.append(MatchOdds(
                    match_id=m["id"], league=m["sport_key"],
                    home=m["home_team"], away=m["away_team"],
                    kickoff_utc=m["commence_time"], market=internal,
                    selection=oc["name"], line=oc.get("point"),
                    book=book, decimal_odds=float(oc["price"])))
    return out

class SampleSource(BaseOddsClient, BaseResultsClient):
    def __init__(self, samples_dir: str) -> None:
        self.samples_dir = samples_dir

    def fetch_odds(self, league_keys: list[str]) -> list[MatchOdds]:
        with open(os.path.join(self.samples_dir, "odds_sample.json"), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        out: list[MatchOdds] = []
        for m in data:
            if league_keys and m["sport_key"] not in league_keys:
                continue
            out.extend(_normalize_match(m))
        return out

    def fetch_history(self, history_code: str) -> pd.DataFrame:
        path = os.path.join(self.samples_dir, f"history_{history_code}_sample.csv")
        if not os.path.exists(path):
            path = os.path.join(self.samples_dir, "history_E0_sample.csv")
        return pd.read_csv(path)
