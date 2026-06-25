import math
import pandas as pd
from config.settings import load_settings
from model.corners_negbin import CornersNegBinModel
from model.corners import CornersPoissonModel
from model.markets import over_under_total
from model.registry import CORNERS_MODELS, build_corners


def _toy():
    rows = []
    teams = ["A", "B", "C"]
    for d in range(1, 13):
        h, a = teams[d % 3], teams[(d + 1) % 3]
        rows.append({"Date": f"2025-01-{d:02d}", "HomeTeam": h, "AwayTeam": a,
                     "HC": 4 + (d % 5), "AC": 3 + (d % 4)})  # varied -> some overdispersion
    return pd.DataFrame(rows)


def test_fit_and_matrix_sums_to_one():
    m = CornersNegBinModel(max_corners=20, xi=0.0)
    m.fit(_toy())
    M = m.score_matrix("A", "B")
    assert M.shape == (21, 21)
    assert math.isclose(M.sum(), 1.0, abs_tol=1e-6)
    r = over_under_total(M, 9.5)
    assert math.isclose(r["over"] + r["under"], 1.0, abs_tol=1e-6)
    assert m.r > 0  # dispersion fitted


def test_unknown_team_raises():
    m = CornersNegBinModel(max_corners=20, xi=0.0)
    m.fit(_toy())
    try:
        m.score_matrix("A", "ZZ")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_corners_registry_and_fallback():
    s = load_settings("settings.yaml")
    assert set(CORNERS_MODELS) == {"poisson", "negbin"}
    assert isinstance(build_corners("poisson", s), CornersPoissonModel)
    assert isinstance(build_corners("negbin", s), CornersNegBinModel)
    assert isinstance(build_corners("unknown", s), CornersPoissonModel)
