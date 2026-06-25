"""Bankroll curve + Monte-Carlo risk of ruin.

Turns flagged signals into a risk picture: how the bankroll evolved on settled bets, and — for
the open bets — the chance of going bust and the spread of outcomes. Variance is real; size for it.
"""
from __future__ import annotations
import numpy as np


def bankroll_curve(profits: list[float], starting: float) -> list[float]:
    """Running bankroll after each settled bet's profit (1-unit-stake P/L values)."""
    bal = starting
    curve = [starting]
    for p in profits:
        bal += p
        curve.append(bal)
    return curve


def monte_carlo_risk(bets: list[dict], starting: float, sims: int = 5000, seed: int = 0) -> dict:
    """Simulate the open-bet sequence many times to estimate risk of ruin + outcome spread.

    Each bet: {"win_prob": p, "odds": decimal_odds, "stake": units}.
    risk_of_ruin = fraction of simulations whose bankroll touches <= 0 at any point.
    """
    if not bets:
        return {"risk_of_ruin": 0.0, "median_final": starting,
                "p05_final": starting, "sims": sims}
    rng = np.random.default_rng(seed)
    wp = np.array([b["win_prob"] for b in bets], dtype=float)
    stake = np.array([b["stake"] for b in bets], dtype=float)
    net = np.array([(b["odds"] - 1.0) * b["stake"] for b in bets], dtype=float)

    finals = np.empty(sims)
    ruined = 0
    for s in range(sims):
        wins = rng.random(len(bets)) < wp
        deltas = np.where(wins, net, -stake)
        bal = starting + np.cumsum(deltas)
        finals[s] = bal[-1]
        if bal.min() <= 0:
            ruined += 1
    return {"risk_of_ruin": ruined / sims,
            "median_final": float(np.median(finals)),
            "p05_final": float(np.percentile(finals, 5)),
            "sims": sims}
