"""Source interfaces + the normalized odds record the pipeline consumes."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class MatchOdds:
    match_id: str
    league: str
    home: str
    away: str
    kickoff_utc: str
    market: str        # internal market id: h2h | totals_goals | totals_corners
    selection: str     # e.g. "Arsenal", "Draw", "Over", "Under"
    line: float | None # half-line for totals, None for h2h
    book: str
    decimal_odds: float

class BaseOddsClient(ABC):
    @abstractmethod
    def fetch_odds(self, league_keys: list[str]) -> list[MatchOdds]: ...

class BaseResultsClient(ABC):
    @abstractmethod
    def fetch_history(self, history_code: str) -> pd.DataFrame: ...
