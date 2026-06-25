import datetime as dt
from config.settings import load_settings
from storage.db import connect, migrate
from storage.repositories import MatchRepo, OddsRepo, BetRepo
from pipeline.clv import compute_clv

def test_compute_clv_beats_close(tmp_path):
    s = load_settings("settings.yaml")
    conn = connect(str(tmp_path / "t.db")); migrate(conn)
    MatchRepo(conn).upsert({"match_id": "m1", "league": "soccer_epl",
        "home": "Arsenal", "away": "Chelsea",
        "kickoff_utc": "2026-06-25T14:00:00Z", "status": "scheduled"})
    now = dt.datetime.utcnow().isoformat()
    BetRepo(conn).insert({"timestamp": now, "match_id": "m1",
        "league": "soccer_epl", "market": "h2h", "selection": "Arsenal",
        "line": None, "model_prob": 0.55, "fair_prob": 0.48, "edge": 0.07,
        "ev": 0.155, "taken_odds": 2.10, "book": "pinnacle", "stake": 1.0,
        "status": "open"})
    OddsRepo(conn).insert_snapshot({"match_id": "m1", "market": "h2h",
        "selection": "Arsenal", "line": None, "book": "pinnacle",
        "decimal_odds": 1.95, "captured_at": now, "snapshot_type": "closing"})
    summary = compute_clv(conn, s)
    assert summary["sample_size"] == 1
    assert summary["pct_positive_clv"] == 100.0
    assert summary["reliable"] is False  # below clv_reliable_min
