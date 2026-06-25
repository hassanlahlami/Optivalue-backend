import numpy as np
import pandas as pd
from config.settings import load_settings
from sources.sample import SampleSource
from sources.canonical import canonical_team, validate_history
from model.markets import btts
from pipeline.run import fit_models, model_prob_for, _consensus_fair_for


def test_btts_market_function():
    M = np.array([[0.4, 0.1], [0.1, 0.4]])  # mass on (0,0) and (1,1)
    r = btts(M)
    assert abs(r["yes"] - 0.4) < 1e-9        # only (1,1) has both teams scoring
    assert abs(r["yes"] + r["no"] - 1.0) < 1e-9


def test_btts_via_model_prob():
    s = load_settings("settings.yaml")
    bundle = fit_models(SampleSource("data/samples"), s)
    yes = model_prob_for(bundle, "club", "Arsenal", "Chelsea", "btts", "Yes", None, s)
    no = model_prob_for(bundle, "club", "Arsenal", "Chelsea", "btts", "No", None, s)
    assert yes is not None and 0.0 < yes < 1.0
    assert abs(yes + no - 1.0) < 1e-9


def test_sharp_consensus_uses_only_sharp_books():
    s = load_settings("settings.yaml")
    object.__setattr__(s, "consensus", "sharp")
    market_books = {
        "pinnacle": {"home": 2.0, "draw": 4.0, "away": 4.0},   # de-vigs to .50/.25/.25
        "softbook": {"home": 1.5, "draw": 4.5, "away": 6.0},   # should be ignored
    }
    best = {"home": ("softbook", 2.1), "draw": ("pinnacle", 4.0), "away": ("softbook", 6.0)}
    fair = _consensus_fair_for(market_books, ["away", "draw", "home"], best, s)
    assert abs(fair["home"] - 0.5) < 1e-9    # from Pinnacle only


def test_canonical_team_normalizes():
    assert canonical_team("Manchester City") == "Man City"
    assert canonical_team("Arsenal") == "Arsenal"


def test_validate_history_reports_quality():
    rep = validate_history(SampleSource("data/samples").fetch_history("E0"))
    assert rep["ok"] is True
    assert rep["has_corners"] is True
    assert rep["has_closing_odds"] is True   # sample carries PSC* columns
    bad = validate_history(pd.DataFrame({"HomeTeam": ["A"]}))
    assert bad["ok"] is False and "FTHG" in bad["missing_columns"]
