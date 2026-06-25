import datetime as dt
from storage.db import connect, migrate
from storage.repositories import MatchRepo, BetRepo, ClvRepo

def make_conn(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    migrate(conn)
    return conn

def test_match_and_bet_roundtrip(tmp_path):
    conn = make_conn(tmp_path)
    MatchRepo(conn).upsert({"match_id": "m1", "league": "soccer_epl",
        "home": "Arsenal", "away": "Chelsea",
        "kickoff_utc": "2026-06-25T14:00:00Z", "status": "scheduled"})
    bet_id = BetRepo(conn).insert({
        "timestamp": dt.datetime.utcnow().isoformat(), "match_id": "m1",
        "league": "soccer_epl", "market": "h2h", "selection": "Arsenal",
        "line": None, "model_prob": 0.55, "fair_prob": 0.50, "edge": 0.05,
        "ev": 0.10, "taken_odds": 2.0, "book": "pinnacle", "stake": 1.0,
        "status": "open"})
    assert isinstance(bet_id, int)
    open_bets = BetRepo(conn).open_bets()
    assert len(open_bets) == 1 and open_bets[0]["selection"] == "Arsenal"

def test_clv_upsert(tmp_path):
    conn = make_conn(tmp_path)
    # Insert a match and bet first to satisfy FK constraint on clv.bet_id
    MatchRepo(conn).upsert({"match_id": "m1", "league": "soccer_epl",
        "home": "Arsenal", "away": "Chelsea",
        "kickoff_utc": "2026-06-25T14:00:00Z", "status": "scheduled"})
    BetRepo(conn).insert({
        "timestamp": dt.datetime.utcnow().isoformat(), "match_id": "m1",
        "league": "soccer_epl", "market": "h2h", "selection": "Arsenal",
        "line": None, "model_prob": 0.55, "fair_prob": 0.50, "edge": 0.05,
        "ev": 0.10, "taken_odds": 2.0, "book": "pinnacle", "stake": 1.0,
        "status": "open"})
    ClvRepo(conn).upsert({"bet_id": 1, "closing_odds": 1.9,
        "closing_fair_prob": 0.52, "clv_price": 0.05, "clv_prob": 0.03,
        "settled_at": "2026-06-25T16:00:00Z"})
    rows = ClvRepo(conn).all()
    assert len(rows) == 1 and rows[0]["bet_id"] == 1
