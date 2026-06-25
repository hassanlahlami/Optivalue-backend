from config.settings import load_settings
from sources.sample import SampleSource
from backtest.clv_backtest import clv_backtest, tune_blend_weight


def test_clv_backtest_runs_with_odds():
    s = load_settings("settings.yaml")
    hist = SampleSource("data/samples").fetch_history("E0")
    r = clv_backtest(hist, s, train_frac=0.5, w=0.5)
    assert "n" in r
    if r["n"] > 0:
        assert "pct_beat_close" in r
        assert "roi" in r
        assert "mean_clv" in r


def test_clv_backtest_reports_no_odds_gracefully():
    import pandas as pd
    s = load_settings("settings.yaml")
    bare = pd.DataFrame({
        "Date": ["10/08/2024", "11/08/2024", "12/08/2024", "13/08/2024"],
        "HomeTeam": ["A", "B", "A", "B"], "AwayTeam": ["B", "A", "B", "A"],
        "FTHG": [1, 2, 0, 1], "FTAG": [0, 2, 1, 1],
    })
    r = clv_backtest(bare, s, train_frac=0.5)
    assert r["n"] == 0 and "note" in r


def test_tune_blend_weight_structure():
    s = load_settings("settings.yaml")
    hist = SampleSource("data/samples").fetch_history("E0")
    out = tune_blend_weight(hist, s, train_frac=0.5)
    assert "all" in out and len(out["all"]) == 5
