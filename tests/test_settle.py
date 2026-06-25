import datetime as dt
import pandas as pd
from config.settings import load_settings
from storage.db import connect, migrate
from storage.repositories import MatchRepo, BetRepo, SettlementRepo
from pipeline.settle import grade_bet, settle_bets, results_from_history

_H2H = {"market": "h2h", "selection": "Arsenal", "line": None, "taken_odds": 2.5,
        "home": "Arsenal", "away": "Chelsea"}


def test_grade_h2h_win():
    g, p = grade_bet(_H2H, {"home_goals": 2, "away_goals": 1})
    assert g == "win" and abs(p - 1.5) < 1e-9


def test_grade_h2h_loss():
    g, p = grade_bet(_H2H, {"home_goals": 0, "away_goals": 1})
    assert g == "loss" and p == -1.0


def test_grade_totals_win_and_push():
    over = {"market": "totals_goals", "selection": "Over", "line": 2.5, "taken_odds": 2.0,
            "home": "A", "away": "B"}
    assert grade_bet(over, {"home_goals": 2, "away_goals": 1})[0] == "win"
    push = {**over, "line": 3.0}
    g, p = grade_bet(push, {"home_goals": 2, "away_goals": 1})
    assert g == "void" and p == 0.0


def test_results_from_history_keys():
    df = pd.DataFrame({"HomeTeam": ["Arsenal"], "AwayTeam": ["Chelsea"],
                       "FTHG": [2], "FTAG": [1], "HC": [7], "AC": [4]})
    m = results_from_history(df)
    assert m["arsenal|chelsea"]["home_goals"] == 2
    assert m["arsenal|chelsea"]["home_corners"] == 7


def test_settle_bets_persists(tmp_path):
    s = load_settings("settings.yaml")
    conn = connect(str(tmp_path / "t.db"))
    migrate(conn)
    MatchRepo(conn).upsert({"match_id": "m1", "league": "x", "home": "Arsenal",
        "away": "Chelsea", "kickoff_utc": "2026-06-25T14:00:00Z", "status": "scheduled"})
    BetRepo(conn).insert({"timestamp": dt.datetime.utcnow().isoformat(), "match_id": "m1",
        "league": "x", "market": "h2h", "selection": "Arsenal", "line": None, "model_prob": 0.6,
        "fair_prob": 0.5, "edge": 0.1, "ev": 0.2, "taken_odds": 2.5, "book": "p",
        "stake": 1.0, "status": "open"})
    summary = settle_bets(conn, {"arsenal|chelsea": {"home_goals": 2, "away_goals": 1}}, s)
    assert summary["settled"] == 1 and summary["wins"] == 1
    assert len(SettlementRepo(conn).all()) == 1
