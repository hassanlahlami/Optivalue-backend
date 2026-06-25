import math
import numpy as np
import pandas as pd
from model.corners import CornersPoissonModel
from model.markets import over_under_total

def _toy():
    rows = []
    teams = ["A", "B", "C"]
    for d in range(1, 13):
        h, a = teams[d % 3], teams[(d + 1) % 3]
        rows.append({"Date": f"2025-01-{d:02d}", "HomeTeam": h, "AwayTeam": a,
                     "HC": 5, "AC": 5})
    return pd.DataFrame(rows)

def test_corners_matrix_sums_to_one():
    m = CornersPoissonModel(max_corners=20, xi=0.0)
    m.fit(_toy())
    M = m.score_matrix("A", "B")
    assert M.shape == (21, 21)
    assert math.isclose(M.sum(), 1.0, abs_tol=1e-6)

def test_corners_over_under():
    m = CornersPoissonModel(max_corners=20, xi=0.0)
    m.fit(_toy())
    M = m.score_matrix("A", "B")
    r = over_under_total(M, 9.5)
    assert math.isclose(r["over"] + r["under"], 1.0, abs_tol=1e-6)

def test_unknown_team_raises():
    m = CornersPoissonModel(max_corners=20, xi=0.0)
    m.fit(_toy())
    try:
        m.score_matrix("A", "ZZ"); assert False
    except KeyError:
        pass
