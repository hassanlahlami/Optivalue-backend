"""Model-quality metrics for 1X2 probability predictions (offline; no odds needed).

A 1X2 prediction is a dict {"home": p, "draw": p, "away": p}. Lower Brier / log-loss = better.
Calibration asks: when we say 60%, does it happen ~60% of the time?
"""
from __future__ import annotations
import math
import numpy as np

OUTCOMES = ("home", "draw", "away")


def brier_score(preds: list[dict], outcomes: list[str]) -> float:
    """Multiclass Brier score: mean over matches of sum_k (p_k - 1{outcome==k})^2."""
    if not preds:
        raise ValueError("no predictions")
    total = 0.0
    for p, y in zip(preds, outcomes):
        total += sum((p[k] - (1.0 if k == y else 0.0)) ** 2 for k in OUTCOMES)
    return total / len(preds)


def log_loss(preds: list[dict], outcomes: list[str], eps: float = 1e-15) -> float:
    """Mean negative log-likelihood of the realized outcome."""
    if not preds:
        raise ValueError("no predictions")
    total = 0.0
    for p, y in zip(preds, outcomes):
        total += -math.log(min(max(p[y], eps), 1.0))
    return total / len(preds)


def calibration_table(probs, hits, bins: int = 10) -> list[dict]:
    """Bin predicted probabilities; report mean predicted vs empirical frequency per bin."""
    probs = np.asarray(probs, dtype=float)
    hits = np.asarray(hits, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (probs >= lo) & (probs <= hi if i == bins - 1 else probs < hi)
        n = int(mask.sum())
        if n == 0:
            continue
        rows.append({"bin_lo": float(lo), "bin_hi": float(hi), "n": n,
                     "mean_pred": float(probs[mask].mean()),
                     "empirical": float(hits[mask].mean())})
    return rows


def expected_calibration_error(probs, hits, bins: int = 10) -> float:
    """Sample-weighted average gap between predicted probability and empirical frequency."""
    probs = np.asarray(probs, dtype=float)
    n = len(probs)
    if n == 0:
        return 0.0
    table = calibration_table(probs, hits, bins)
    return float(sum(r["n"] / n * abs(r["mean_pred"] - r["empirical"]) for r in table))
