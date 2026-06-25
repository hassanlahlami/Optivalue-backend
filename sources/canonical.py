"""Data-quality layer: one place to canonicalize team names and validate result history.

Different sources spell teams differently (Understat "Manchester City" vs odds "Man City").
canonical_team() normalizes to The Odds API spelling so model history and odds line up.
validate_history() guards a results DataFrame before it's fed to a model fit.
"""
from __future__ import annotations
import pandas as pd

# Source spelling -> The Odds API spelling. Extend as needed.
ALIASES = {
    "Manchester City": "Man City", "Manchester Utd": "Man United", "Manchester United": "Man United",
    "Newcastle United": "Newcastle", "Wolverhampton Wanderers": "Wolves",
    "Nottingham Forest": "Nott'm Forest", "Tottenham Hotspur": "Tottenham", "Spurs": "Tottenham",
    "Brighton & Hove Albion": "Brighton", "West Ham United": "West Ham",
    "United States": "USA", "South Korea": "Korea Republic", "IR Iran": "Iran",
    "Ivory Coast": "Cote d'Ivoire",
}

REQUIRED_COLS = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}


def canonical_team(name: str) -> str:
    s = str(name).strip()
    return ALIASES.get(s, s)


def validate_history(df: pd.DataFrame) -> dict:
    """Report data-quality issues in a results DataFrame (rows, missing cols, unusable rows)."""
    cols = set(df.columns)
    missing = sorted(REQUIRED_COLS - cols)
    n = len(df)
    bad = 0
    if {"FTHG", "FTAG"} <= cols and n:
        bad = int(df[["FTHG", "FTAG"]].isna().any(axis=1).sum())
    return {
        "rows": n,
        "missing_columns": missing,
        "unusable_rows": bad if not missing else n,
        "has_xg": {"HxG", "AxG"} <= cols,
        "has_corners": {"HC", "AC"} <= cols,
        "has_closing_odds": {"PSCH", "PSCD", "PSCA"} <= cols,
        "ok": not missing and n > 0,
    }
