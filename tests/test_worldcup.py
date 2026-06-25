"""World Cup 2026 / international group: separate model, no corners, club isolation."""
from config.settings import load_settings
from sources.sample import SampleSource
from pipeline.run import fit_models, model_prob_for


def test_international_group_is_fitted_separately():
    s = load_settings("settings.yaml")
    bundle = fit_models(SampleSource("data/samples"), s)
    # Club and international teams must not share a fit.
    assert "club" in bundle.goals
    assert "international" in bundle.goals
    # No free corner data for internationals -> corners auto-disabled for that group.
    assert "international" not in bundle.corners


def test_world_cup_match_is_priced():
    s = load_settings("settings.yaml")
    bundle = fit_models(SampleSource("data/samples"), s)
    p = model_prob_for(bundle, "international", "Argentina", "Brazil",
                        "h2h", "Argentina", None, s)
    assert p is not None and 0.0 < p < 1.0
    # corners market returns None for the international group
    assert model_prob_for(bundle, "international", "Argentina", "Brazil",
                          "totals_corners", "Over", 9.5, s) is None


def test_group_isolation():
    s = load_settings("settings.yaml")
    bundle = fit_models(SampleSource("data/samples"), s)
    # A club team is unknown to the international model (and vice versa).
    assert model_prob_for(bundle, "international", "Arsenal", "Chelsea",
                          "h2h", "Arsenal", None, s) is None
    assert model_prob_for(bundle, "club", "Argentina", "Brazil",
                          "h2h", "Argentina", None, s) is None
