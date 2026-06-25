from config.settings import load_settings
from sources.sample import SampleSource
from backtest.run import holdout_backtest


def test_holdout_backtest_runs_on_sample():
    s = load_settings("settings.yaml")
    hist = SampleSource("data/samples").fetch_history("E0")
    r = holdout_backtest(hist, s, train_frac=0.6)
    assert r["sample_size"] >= 1
    assert 0.0 <= r["brier"] <= 2.0
    assert 0.0 <= r["baseline_brier"] <= 2.0
    assert "calibration_home" in r
