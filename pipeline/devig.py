"""Convert bookmaker decimal odds to fair (de-vigged) probabilities.

Three methods, all returning probabilities that sum to 1:
- proportional: divide each implied prob by their sum (simple, default).
- power:        raise implied probs to a common exponent k so they sum to 1.
- shin:         Shin's model estimating insider-trading proportion z.
"""
from __future__ import annotations
from scipy.optimize import brentq

def implied_prob(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {decimal_odds}")
    return 1.0 / decimal_odds

def _proportional(raw: list[float]) -> list[float]:
    total = sum(raw)
    return [r / total for r in raw]

def _power(raw: list[float]) -> list[float]:
    # Find k such that sum(r**k) == 1. Booksum > 1 => k > 1.
    def f(k: float) -> float:
        return sum(r ** k for r in raw) - 1.0
    k = brentq(f, 0.0001, 100.0)
    return [r ** k for r in raw]

def _shin(raw: list[float]) -> list[float]:
    # Shin (1992): p_i = (sqrt(z^2 + 4(1-z) r_i^2 / B) - z) / (2(1-z)), B = sum(raw).
    booksum = sum(raw)
    def probs(z: float) -> list[float]:
        return [((z * z + 4 * (1 - z) * (r * r) / booksum) ** 0.5 - z) / (2 * (1 - z))
                for r in raw]
    def f(z: float) -> float:
        return sum(probs(z)) - 1.0
    z = brentq(f, 1e-9, 0.5)
    return probs(z)

_METHODS = {"proportional": _proportional, "power": _power, "shin": _shin}

def devig(odds: list[float], method: str = "proportional") -> list[float]:
    if method not in _METHODS:
        raise ValueError(f"unknown devig method: {method}")
    raw = [implied_prob(o) for o in odds]
    return _METHODS[method](raw)
