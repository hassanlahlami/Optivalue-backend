from config.settings import load_settings
from sources.sample import SampleSource
from model.registry import GOALS_MODELS, build_goals, compare_models
from model.dixon_coles import DixonColesModel
from model.bivariate_poisson import BivariatePoissonModel


def test_registry_has_both_models():
    assert "dixon_coles" in GOALS_MODELS
    assert "bivariate_poisson" in GOALS_MODELS


def test_build_goals_and_unknown_fallback():
    s = load_settings("settings.yaml")
    assert isinstance(build_goals("dixon_coles", s), DixonColesModel)
    assert isinstance(build_goals("bivariate_poisson", s), BivariatePoissonModel)
    assert isinstance(build_goals("nonexistent", s), DixonColesModel)  # safe fallback


def test_compare_models_ranks_all_registered():
    s = load_settings("settings.yaml")
    hist = SampleSource("data/samples").fetch_history("E0")
    ranked = compare_models(hist, s)
    assert {r["model"] for r in ranked} == set(GOALS_MODELS)  # every registered model appears
    with_results = [r for r in ranked if r.get("sample_size", 0) > 0]
    briers = [r["brier"] for r in with_results]
    assert briers == sorted(briers)  # ranked ascending (best first)
