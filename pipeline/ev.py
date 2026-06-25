"""Edge, expected value, line shopping, and stake sizing — all single-selection."""
from __future__ import annotations

def best_price(quotes: list[tuple[str, float]]) -> tuple[str, float]:
    if not quotes:
        raise ValueError("no quotes to shop")
    return max(quotes, key=lambda q: q[1])

def edge(model_prob: float, fair_prob: float) -> float:
    return model_prob - fair_prob

def expected_value(model_prob: float, decimal_odds: float) -> float:
    return model_prob * decimal_odds - 1.0

def kelly_stake(model_prob: float, decimal_odds: float, fraction: float, flat: float) -> float:
    if fraction <= 0:
        return flat
    b = decimal_odds - 1.0
    q = 1.0 - model_prob
    f_star = (b * model_prob - q) / b
    return max(0.0, fraction * f_star)

def passes(ev: float, threshold: float) -> bool:
    return ev > threshold
