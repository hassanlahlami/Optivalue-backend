import datetime as dt
import json
import os
from fastapi.testclient import TestClient
from config.settings import load_settings
from storage.db import connect, migrate
from storage.repositories import MatchRepo, BetRepo
from api.app import create_app


def _setup(tmp_path, with_bet=False):
    s = load_settings("settings.yaml")
    db = str(tmp_path / "t.db")
    conn = connect(db)
    migrate(conn)
    bid = None
    if with_bet:
        MatchRepo(conn).upsert({"match_id": "m1", "league": "x", "home": "A", "away": "B",
            "kickoff_utc": "2026-06-25T14:00:00Z", "status": "scheduled"})
        bid = BetRepo(conn).insert({"timestamp": dt.datetime.utcnow().isoformat(),
            "match_id": "m1", "league": "x", "market": "h2h", "selection": "A", "line": None,
            "model_prob": 0.6, "fair_prob": 0.5, "edge": 0.1, "ev": 0.2, "taken_odds": 2.0,
            "book": "p", "stake": 1.0, "status": "open"})
    conn.close()
    object.__setattr__(s, "db_path", db)
    object.__setattr__(s, "reports_dir", str(tmp_path / "out"))
    return s, bid


def test_track_bet_placed(tmp_path):
    s, bid = _setup(tmp_path, with_bet=True)
    c = TestClient(create_app(s))
    assert c.post(f"/api/bets/{bid}/placed", json={"placed": True}).json()["placed"] is True
    assert c.get("/api/bets").json()[0]["placed"] == 1
    c.post(f"/api/bets/{bid}/placed", json={"placed": False})
    assert c.get("/api/bets").json()[0]["placed"] == 0


def test_report_card_unavailable_then_available(tmp_path):
    s, _ = _setup(tmp_path)
    c = TestClient(create_app(s))
    assert c.get("/api/report-card").json()["available"] is False
    os.makedirs(s.reports_dir, exist_ok=True)
    with open(os.path.join(s.reports_dir, "model_report_card.json"), "w", encoding="utf-8") as fh:
        json.dump({"sample_size": 10, "brier": 0.4, "baseline_brier": 0.6}, fh)
    out = c.get("/api/report-card").json()
    assert out["available"] is True and out["brier"] == 0.4
