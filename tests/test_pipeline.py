from config.settings import load_settings
from storage.db import connect, migrate
from sources.sample import SampleSource
from pipeline.run import fit_models, run_daily

def test_run_daily_dryrun(tmp_path):
    s = load_settings("settings.yaml")
    src = SampleSource("data/samples")
    bundle = fit_models(src, s)
    conn = connect(str(tmp_path / "t.db")); migrate(conn)
    date = "2026-06-25"
    flagged = run_daily(src, bundle, conn, s, date)
    assert isinstance(flagged, list)
    for b in flagged:
        assert b["ev"] > s.ev_threshold
        assert b["best_odds"] >= 1.0
        assert b["market"] in ("h2h", "totals_goals", "totals_corners")
    from storage.repositories import BetRepo
    assert len(BetRepo(conn).list()) == len(flagged)
