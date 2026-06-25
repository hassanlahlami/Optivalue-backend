import math
import numpy as np
import pandas as pd
from model.dixon_coles import DixonColesModel

def _toy_history():
    # Symmetric round-robin so fitted strengths are near-equal.
    rows = []
    teams = ["A", "B", "C"]
    for d in range(1, 13):
        h, a = teams[d % 3], teams[(d + 1) % 3]
        rows.append({"Date": f"2025-01-{d:02d}", "HomeTeam": h, "AwayTeam": a,
                     "FTHG": 1, "FTAG": 1})
    return pd.DataFrame(rows)

def test_fit_and_score_matrix_sums_to_one():
    m = DixonColesModel(max_goals=8, xi=0.0)
    m.fit(_toy_history())
    M = m.score_matrix("A", "B")
    assert M.shape == (9, 9)
    assert math.isclose(M.sum(), 1.0, abs_tol=1e-6)

def test_unknown_team_raises():
    m = DixonColesModel(max_goals=8, xi=0.0)
    m.fit(_toy_history())
    try:
        m.score_matrix("A", "ZZZ")
        assert False, "expected KeyError"
    except KeyError:
        pass

def test_markets_derivable():
    from model.markets import one_x_two, over_under_total
    m = DixonColesModel(max_goals=8, xi=0.0)
    m.fit(_toy_history())
    M = m.score_matrix("A", "B")
    r = one_x_two(M)
    assert math.isclose(r["home"] + r["draw"] + r["away"], 1.0, abs_tol=1e-6)
    ou = over_under_total(M, 2.5)
    assert math.isclose(ou["over"] + ou["under"], 1.0, abs_tol=1e-6)
