import datetime as dt
from config.settings import load_settings
from storage.db import connect, migrate
from storage.repositories import MatchRepo, OddsRepo, BetRepo
from sources.sample import SampleSource
from backtest.clv_backtest import walk_forward_clv
from pipeline.clv import compute_clv
from pipeline.run import fit_models


def test_walk_forward_runs():
    s = load_settings("settings.yaml")
    hist = SampleSource("data/samples").fetch_history("E0")
    r = walk_forward_clv(hist, s, folds=3, w=0.5)
    assert "n" in r and "folds" in r and r["folds"] == 3


def test_clv_summary_has_significance_fields(tmp_path):
    s = load_settings("settings.yaml")
    conn = connect(str(tmp_path / "t.db"))
    migrate(conn)
    now = dt.datetime.utcnow().isoformat()
    MatchRepo(conn).upsert({"match_id": "m1", "league": "x", "home": "A", "away": "B",
        "kickoff_utc": "2026-06-25T14:00:00Z", "status": "scheduled"})
    for _ in range(3):
        BetRepo(conn).insert({"timestamp": now, "match_id": "m1", "league": "x", "market": "h2h",
            "selection": "A", "line": None, "model_prob": 0.6, "fair_prob": 0.5, "edge": 0.1,
            "ev": 0.2, "taken_odds": 2.10, "book": "p", "stake": 1.0, "status": "open"})
    OddsRepo(conn).insert_snapshot({"match_id": "m1", "market": "h2h", "selection": "A",
        "line": None, "book": "p", "decimal_odds": 1.95, "captured_at": now,
        "snapshot_type": "closing"})
    out = compute_clv(conn, s)
    assert "clv_price_ci_low" in out and "significant" in out
    assert out["significant"] is False  # n far below clv_reliable_min


def test_calibrator_fits_when_enabled():
    s = load_settings("settings.yaml")
    object.__setattr__(s, "calibrate_enabled", True)
    object.__setattr__(s, "calibrate_min_samples", 10)
    bundle = fit_models(SampleSource("data/samples"), s)
    assert "club" in bundle.calibrators
