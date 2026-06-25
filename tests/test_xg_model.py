import math
import pandas as pd
from model.xg_dixon_coles import XGDixonColesModel, _xg_columns
from model.markets import one_x_two


def _toy_with_xg():
    rows = []
    teams = ["A", "B", "C"]
    for d in range(1, 13):
        h, a = teams[d % 3], teams[(d + 1) % 3]
        rows.append({"Date": f"2025-01-{d:02d}", "HomeTeam": h, "AwayTeam": a,
                     "FTHG": 1, "FTAG": 1,
                     "HxG": 2.5 if h == "A" else 1.0,   # A creates more, concedes less
                     "AxG": 2.5 if a == "A" else 1.0})
    return pd.DataFrame(rows)


def test_xg_columns_detected():
    assert _xg_columns(_toy_with_xg()) == ("HxG", "AxG")


def test_fits_on_xg_and_strong_team_favoured():
    m = XGDixonColesModel(max_goals=8, xi=0.0)
    m.fit(_toy_with_xg())
    assert m.fit_on_xg is True
    M = m.score_matrix("A", "B")
    assert math.isclose(M.sum(), 1.0, abs_tol=1e-6)
    r = one_x_two(M)
    assert r["home"] > r["away"]  # A's higher xG -> favoured vs B at home


def test_falls_back_to_goals_without_xg():
    df = _toy_with_xg().drop(columns=["HxG", "AxG"])
    m = XGDixonColesModel(max_goals=8, xi=0.0)
    m.fit(df)
    assert m.fit_on_xg is False
