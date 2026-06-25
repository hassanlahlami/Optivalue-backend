import pandas as pd
from config.settings import load_settings
from sources.sample import SampleSource
from model.venue_dixon_coles import VenueAwareDixonColesModel, _neutral_array
from model.markets import one_x_two
from model.registry import GOALS_MODELS
from pipeline.run import fit_models


def _toy_home_wins():
    rows = []
    teams = ["A", "B", "C"]
    for d in range(1, 13):
        h, a = teams[d % 3], teams[(d + 1) % 3]
        rows.append({"Date": f"2025-01-{d:02d}", "HomeTeam": h, "AwayTeam": a,
                     "FTHG": 2, "FTAG": 0, "neutral": False})
    return pd.DataFrame(rows)


def test_neutral_array_parses_mixed_values():
    arr = _neutral_array(pd.DataFrame({"neutral": ["TRUE", "False", 1, "no"]}))
    assert list(arr) == [True, False, True, False]


def test_default_neutral_removes_home_edge():
    m = VenueAwareDixonColesModel(max_goals=8, xi=0.0)
    m.fit(_toy_home_wins())                    # strong home advantage in the data
    home_prob_with_edge = one_x_two(m.score_matrix("A", "B"))["home"]
    m.default_neutral = True
    home_prob_neutral = one_x_two(m.score_matrix("A", "B"))["home"]
    assert home_prob_neutral < home_prob_with_edge


def test_registry_includes_venue_model():
    assert "venue_dixon_coles" in GOALS_MODELS


def test_pipeline_sets_neutral_for_international_group():
    s = load_settings("settings.yaml")
    object.__setattr__(s, "goals_model", "venue_dixon_coles")
    bundle = fit_models(SampleSource("data/samples"), s)
    assert bundle.goals["international"].default_neutral is True
    assert bundle.goals["club"].default_neutral is False
