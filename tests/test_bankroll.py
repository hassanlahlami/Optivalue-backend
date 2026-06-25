from pipeline.bankroll import bankroll_curve, monte_carlo_risk


def test_bankroll_curve_accumulates():
    assert bankroll_curve([1.0, -1.0, 2.0], 10.0) == [10.0, 11.0, 10.0, 12.0]


def test_monte_carlo_empty_is_safe():
    r = monte_carlo_risk([], 100.0)
    assert r["risk_of_ruin"] == 0.0 and r["median_final"] == 100.0


def test_monte_carlo_sure_loss_is_ruin():
    # one bet, never wins, stake equals the whole bankroll -> always ruined.
    r = monte_carlo_risk([{"win_prob": 0.0, "odds": 2.0, "stake": 100.0}], 100.0, sims=200)
    assert r["risk_of_ruin"] == 1.0
