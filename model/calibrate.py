"""Isotonic probability calibration via Pool Adjacent Violators (pure numpy, no sklearn).

Fixes systematic over/under-confidence: learns a monotonic map from predicted probability to
the empirically observed frequency. Fit on (predicted_prob, outcome 0/1) pairs, then transform.
"""
from __future__ import annotations
import numpy as np


def _pava(y: np.ndarray) -> np.ndarray:
    """Non-decreasing isotonic fit of y (already ordered by increasing x). Unweighted PAVA."""
    blocks: list[list[float]] = []  # each block: [value, count]
    for yi in y:
        blocks.append([float(yi), 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, c2 = blocks.pop()
            v1, c1 = blocks.pop()
            blocks.append([(v1 * c1 + v2 * c2) / (c1 + c2), c1 + c2])
    out: list[float] = []
    for v, c in blocks:
        out.extend([v] * int(c))
    return np.asarray(out, dtype=float)


class IsotonicCalibrator:
    def __init__(self) -> None:
        self._x: np.ndarray | None = None
        self._y: np.ndarray | None = None

    def fit(self, prob, hit) -> "IsotonicCalibrator":
        prob = np.asarray(prob, dtype=float)
        hit = np.asarray(hit, dtype=float)
        order = np.argsort(prob, kind="mergesort")
        self._x = prob[order]
        self._y = _pava(hit[order])
        return self

    def transform(self, prob):
        if self._x is None or self._y is None:
            raise RuntimeError("IsotonicCalibrator is not fitted")
        return np.interp(np.asarray(prob, dtype=float), self._x, self._y)
