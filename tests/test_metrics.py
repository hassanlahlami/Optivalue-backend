import math
from backtest.metrics import (
    brier_score, log_loss, calibration_table, expected_calibration_error,
)


def test_brier_perfect_is_zero():
    assert brier_score([{"home": 1.0, "draw": 0.0, "away": 0.0}], ["home"]) == 0.0


def test_brier_known_value():
    # outcome home: (0.5-1)^2 + 0.3^2 + 0.2^2 = 0.25 + 0.09 + 0.04 = 0.38
    assert math.isclose(brier_score([{"home": 0.5, "draw": 0.3, "away": 0.2}], ["home"]), 0.38)


def test_log_loss_known_value():
    assert math.isclose(log_loss([{"home": 0.5, "draw": 0.3, "away": 0.2}], ["home"]),
                        -math.log(0.5))


def test_calibration_perfect_has_zero_ece():
    probs = [0.0, 0.0, 1.0, 1.0]
    hits = [0, 0, 1, 1]
    assert math.isclose(expected_calibration_error(probs, hits, bins=10), 0.0)


def test_calibration_table_reports_bins():
    table = calibration_table([0.05, 0.15, 0.16], [0, 1, 0], bins=10)
    # 0.05 -> first bin; 0.15 and 0.16 -> second bin
    assert len(table) == 2
    assert table[1]["n"] == 2
