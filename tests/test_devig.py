import math
from pipeline.devig import implied_prob, devig

def test_implied_prob():
    assert implied_prob(2.0) == 0.5
    assert math.isclose(implied_prob(4.0), 0.25)

def test_proportional_sums_to_one():
    fair = devig([2.0, 4.0, 4.0], method="proportional")
    assert math.isclose(sum(fair), 1.0, abs_tol=1e-9)
    # raw implied = .5,.25,.25 = 1.0 overround here -> unchanged
    assert math.isclose(fair[0], 0.5, abs_tol=1e-9)

def test_proportional_removes_overround():
    # Two-way market priced with vig: 1.90 / 1.90 -> implied .526 each, sum 1.052
    fair = devig([1.90, 1.90], method="proportional")
    assert math.isclose(sum(fair), 1.0, abs_tol=1e-9)
    assert math.isclose(fair[0], 0.5, abs_tol=1e-9)

def test_power_and_shin_sum_to_one():
    for m in ("power", "shin"):
        fair = devig([1.5, 3.5, 7.0], method=m)
        assert math.isclose(sum(fair), 1.0, abs_tol=1e-6)
        assert all(0 < p < 1 for p in fair)
