import os
from reports.daily import render as render_daily
from reports.clv import render as render_clv

def test_daily_report_files(tmp_path):
    flagged = [{"home": "Arsenal", "away": "Chelsea", "market": "h2h",
        "selection": "Arsenal", "line": None, "model_prob": 0.55,
        "fair_prob": 0.48, "edge": 0.07, "ev": 0.155, "best_odds": 2.10,
        "book": "pinnacle", "stake": 1.0, "league": "soccer_epl"}]
    csv_path, html_path = render_daily(flagged, str(tmp_path), "2026-06-25")
    assert os.path.exists(csv_path) and os.path.exists(html_path)
    assert "Arsenal" in open(html_path, encoding="utf-8").read()

def test_daily_report_empty(tmp_path, capsys):
    render_daily([], str(tmp_path), "2026-06-25")
    assert "No value bets" in capsys.readouterr().out

def test_clv_report_files(tmp_path):
    summary = {"sample_size": 3, "pct_positive_clv": 66.7, "mean_clv_price": 0.02,
        "mean_clv_prob": 0.01, "reliable": False, "by_league": {"soccer_epl": 0.02},
        "by_market": {"h2h": 0.02}}
    csv_path, html_path = render_clv(summary, str(tmp_path))
    assert os.path.exists(csv_path) and os.path.exists(html_path)
    assert "not yet reliable" in open(html_path, encoding="utf-8").read().lower()
