import math
import numpy as np
from model.markets import one_x_two, over_under_total, normalize

def test_one_x_two_symmetric():
    # 2x2 matrix, equal home/away -> home prob == away prob, all sum to 1
    M = np.array([[0.25, 0.25], [0.25, 0.25]])
    r = one_x_two(M)
    assert math.isclose(r["home"] + r["draw"] + r["away"], 1.0)
    assert math.isclose(r["home"], r["away"])
    assert math.isclose(r["draw"], 0.5)  # cells (0,0) and (1,1)

def test_over_under_split():
    M = np.array([[0.4, 0.1], [0.1, 0.4]])  # totals: 0,1,1,2
    r = over_under_total(M, 1.5)
    # over 1.5 means total >= 2 -> only cell (1,1)=0.4
    assert math.isclose(r["over"], 0.4)
    assert math.isclose(r["under"], 0.6)
    assert math.isclose(r["over"] + r["under"], 1.0)

def test_normalize():
    M = np.array([[1.0, 1.0], [1.0, 1.0]])
    N = normalize(M)
    assert math.isclose(N.sum(), 1.0)
