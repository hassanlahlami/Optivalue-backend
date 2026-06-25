import math
from pipeline.ev import best_price, edge, expected_value, kelly_stake, passes

def test_best_price_picks_max():
    assert best_price([("a", 1.9), ("b", 2.1), ("c", 2.0)]) == ("b", 2.1)

def test_edge():
    assert math.isclose(edge(0.55, 0.50), 0.05)

def test_expected_value():
    # 55% at 2.0 -> EV = .55*2 - 1 = 0.10
    assert math.isclose(expected_value(0.55, 2.0), 0.10)
    # fair coin at 2.0 -> EV 0
    assert math.isclose(expected_value(0.5, 2.0), 0.0)

def test_kelly_flat_when_fraction_zero():
    assert kelly_stake(0.55, 2.0, fraction=0.0, flat=1.0) == 1.0

def test_kelly_fractional_positive_edge():
    # full kelly f* = (bp - q)/b, b=1 (odds 2.0), p=.55 -> .10; half kelly -> .05
    s = kelly_stake(0.55, 2.0, fraction=0.5, flat=1.0)
    assert math.isclose(s, 0.05, abs_tol=1e-9)

def test_kelly_no_negative_stake():
    assert kelly_stake(0.40, 2.0, fraction=1.0, flat=1.0) == 0.0

def test_passes_strict():
    assert passes(0.01, 0.0) is True
    assert passes(0.0, 0.0) is False
