"""Turn a joint score-probability matrix into market probabilities.

M[i, j] = P(home scores i, away scores j). All functions assume M is normalized
(sums to ~1); call normalize(M) first if unsure.
"""
from __future__ import annotations
import numpy as np

def normalize(M: np.ndarray) -> np.ndarray:
    total = M.sum()
    return M / total

def one_x_two(M: np.ndarray) -> dict[str, float]:
    home = float(np.tril(M, -1).sum())   # i > j
    away = float(np.triu(M, 1).sum())    # j > i
    draw = float(np.trace(M))            # i == j
    return {"home": home, "draw": draw, "away": away}

def btts(M: np.ndarray) -> dict[str, float]:
    """Both teams to score: yes = P(home >= 1 and away >= 1)."""
    yes = float(M[1:, 1:].sum())
    return {"yes": yes, "no": 1.0 - yes}

def over_under_total(M: np.ndarray, line: float) -> dict[str, float]:
    n_rows, n_cols = M.shape
    over = 0.0
    for i in range(n_rows):
        for j in range(n_cols):
            if (i + j) > line:
                over += float(M[i, j])
    return {"over": over, "under": 1.0 - over}
