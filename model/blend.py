"""Blend model probabilities toward the market — the proven edge unlock.

The de-vigged sharp price is itself the strongest "model". A weighted blend of our model and
the market typically beats either alone:  final = w*model + (1-w)*market, renormalized.
w is chosen by backtest (closer to 0 trusts the market more). w in [0, 1].
"""
from __future__ import annotations


def blend_probs(model: dict, market: dict, w: float) -> dict:
    if not 0.0 <= w <= 1.0:
        raise ValueError(f"w must be in [0, 1], got {w}")
    keys = set(model) | set(market)
    raw = {k: w * model.get(k, 0.0) + (1.0 - w) * market.get(k, 0.0) for k in keys}
    total = sum(raw.values())
    if total <= 0:
        return raw
    return {k: v / total for k, v in raw.items()}
