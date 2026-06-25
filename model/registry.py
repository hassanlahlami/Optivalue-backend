"""Swappable goals-model registry + head-to-head comparison via the backtest harness.

Phase 3 discipline: models compete on out-of-sample skill. Register a model here, then
`compare_models` ranks every registered model by Brier score on the same holdout, so a new
model only earns its way into production (settings.goals_model) by beating the incumbent.
"""
from __future__ import annotations
from model.dixon_coles import DixonColesModel
from model.bivariate_poisson import BivariatePoissonModel
from model.venue_dixon_coles import VenueAwareDixonColesModel
from model.xg_dixon_coles import XGDixonColesModel
from model.corners import CornersPoissonModel
from model.corners_negbin import CornersNegBinModel

# name -> factory(settings) -> BaseModel
GOALS_MODELS = {
    "dixon_coles": lambda s: DixonColesModel(max_goals=s.max_goals, xi=s.time_decay_xi),
    "bivariate_poisson": lambda s: BivariatePoissonModel(max_goals=s.max_goals, xi=s.time_decay_xi),
    "venue_dixon_coles": lambda s: VenueAwareDixonColesModel(max_goals=s.max_goals, xi=s.time_decay_xi),
    "xg_dixon_coles": lambda s: XGDixonColesModel(max_goals=s.max_goals, xi=s.time_decay_xi),
}

CORNERS_MODELS = {
    "poisson": lambda s: CornersPoissonModel(max_corners=s.max_corners, xi=s.time_decay_xi),
    "negbin": lambda s: CornersNegBinModel(max_corners=s.max_corners, xi=s.time_decay_xi),
}


def build_goals(name: str, settings):
    """Build the configured goals model (falls back to dixon_coles for an unknown name)."""
    factory = GOALS_MODELS.get(name) or GOALS_MODELS["dixon_coles"]
    return factory(settings)


def build_corners(name: str, settings):
    """Build the configured corners model (falls back to poisson for an unknown name)."""
    factory = CORNERS_MODELS.get(name) or CORNERS_MODELS["poisson"]
    return factory(settings)


def compare_models(history, settings, names: list[str] | None = None) -> list[dict]:
    """Run each registered model through the holdout backtest; return results ranked by Brier."""
    from backtest.run import holdout_backtest
    names = names or list(GOALS_MODELS)
    out = []
    for name in names:
        metrics = holdout_backtest(history, settings, model_factory=GOALS_MODELS[name])
        out.append({"model": name, **metrics})
    out.sort(key=lambda r: r.get("brier", float("inf")))
    return out
