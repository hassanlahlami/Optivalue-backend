import math
from config.settings import load_settings
from storage.db import connect, migrate
from sources.sample import SampleSource
from pipeline.run import fit_models, run_daily


def _run(blend_weight, tmp_path):
    s = load_settings("settings.yaml")
    object.__setattr__(s, "blend_weight", blend_weight)
    src = SampleSource("data/samples")
    bundle = fit_models(src, s)
    conn = connect(str(tmp_path / "t.db"))
    migrate(conn)
    return run_daily(src, bundle, conn, s, "2026-06-25")


def test_pure_market_makes_model_prob_equal_fair(tmp_path):
    # blend_weight=0 -> final prob is exactly the de-vigged market prob.
    flagged = _run(0.0, tmp_path)
    for b in flagged:
        assert math.isclose(b["model_prob"], b["fair_prob"], abs_tol=1e-9)
        assert math.isclose(b["edge"], 0.0, abs_tol=1e-9)


def test_pure_model_differs_from_market(tmp_path):
    # blend_weight=1 -> at least one flagged bet has model prob != fair prob (real edge).
    flagged = _run(1.0, tmp_path)
    assert any(not math.isclose(b["model_prob"], b["fair_prob"], abs_tol=1e-6) for b in flagged)
