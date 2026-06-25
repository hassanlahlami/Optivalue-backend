import math
import pandas as pd
from scipy.stats import poisson
from model.bivariate_poisson import BivariatePoissonModel, _biv_pmf
from model.markets import one_x_two


def _toy():
    rows = []
    teams = ["A", "B", "C"]
    for d in range(1, 13):
        h, a = teams[d % 3], teams[(d + 1) % 3]
        rows.append({"Date": f"2025-01-{d:02d}", "HomeTeam": h, "AwayTeam": a,
                     "FTHG": 1, "FTAG": 1})
    return pd.DataFrame(rows)


def test_biv_pmf_reduces_to_independent_when_l3_zero():
    p = _biv_pmf(2, 1, 1.5, 1.2, 0.0)
    expect = poisson.pmf(2, 1.5) * poisson.pmf(1, 1.2)
    assert math.isclose(p, expect, rel_tol=1e-9)


def test_fit_and_matrix_sums_to_one():
    m = BivariatePoissonModel(max_goals=8, xi=0.0)
    m.fit(_toy())
    M = m.score_matrix("A", "B")
    assert M.shape == (9, 9)
    assert math.isclose(M.sum(), 1.0, abs_tol=1e-6)
    r = one_x_two(M)
    assert math.isclose(r["home"] + r["draw"] + r["away"], 1.0, abs_tol=1e-6)


def test_unknown_team_raises():
    m = BivariatePoissonModel(max_goals=8, xi=0.0)
    m.fit(_toy())
    try:
        m.score_matrix("A", "ZZ")
        assert False, "expected KeyError"
    except KeyError:
        pass
