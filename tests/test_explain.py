"""Explanation generation: offline template + no-key fallback (no network in tests)."""
from pipeline.explain import template_explanation, build_explainer, TemplateExplainer

BET = {"home": "Arsenal", "away": "Chelsea", "market": "h2h", "selection": "Arsenal",
       "line": None, "model_prob": 0.55, "fair_prob": 0.48, "edge": 0.07, "ev": 0.155,
       "best_odds": 2.10, "book": "pinnacle"}


def test_template_explanation_mentions_key_facts():
    txt = template_explanation(BET)
    assert "Arsenal" in txt
    assert "pinnacle" in txt
    assert "%" in txt          # quotes the probabilities/edge
    assert "55.0%" in txt      # model probability rendered


def test_build_explainer_falls_back_without_key():
    class S:
        llm_enabled = True
        llm_api_key = None     # no key -> must not attempt a network call
        llm_base_url = "https://example/v1"
        llm_model = "m"
        cache_dir = ".cache"
    ex = build_explainer(S())
    assert isinstance(ex, TemplateExplainer)
    assert "Arsenal" in ex.explain(BET)
