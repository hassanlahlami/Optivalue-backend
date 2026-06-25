"""Bivariate Poisson goals model (Karlis & Ntzoufras).

Independent Poisson assumes home and away goals are uncorrelated; in reality they are slightly
positively correlated (cagey games stay low, open games go high), which independent Poisson
under-prices on draws. The bivariate Poisson adds a shared covariance component lambda3:
  X = W1 + W3, Y = W2 + W3, with W1~Pois(l1), W2~Pois(l2), W3~Pois(l3).
When l3 = 0 it reduces to independent Poisson. Same attack/defense/home-advantage structure as
Dixon-Coles, fit by time-decay-weighted MLE — so the registry can compare them like-for-like.

History columns (football-data.co.uk): Date, HomeTeam, AwayTeam, FTHG, FTAG.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .base import BaseModel
from .markets import normalize


def _biv_pmf(x: int, y: int, l1: float, l2: float, l3: float) -> float:
    """P(X=x, Y=y) under the bivariate Poisson."""
    total = 0.0
    ratio = l3 / (l1 * l2) if l1 > 0 and l2 > 0 else 0.0
    for k in range(min(x, y) + 1):
        total += math.comb(x, k) * math.comb(y, k) * math.factorial(k) * (ratio ** k)
    return math.exp(-(l1 + l2 + l3)) * (l1 ** x) / math.factorial(x) \
        * (l2 ** y) / math.factorial(y) * total


class BivariatePoissonModel(BaseModel):
    def __init__(self, max_goals: int = 10, xi: float = 0.0018) -> None:
        self.max_goals = max_goals
        self.xi = xi
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.gamma: float = 0.0
        self.lambda3: float = 0.0

    def fit(self, history: pd.DataFrame) -> None:
        df = history.copy()
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        tmax = df["Date"].max()
        weights = np.exp(-self.xi * (tmax - df["Date"]).dt.days.to_numpy())
        h_idx = df["HomeTeam"].map(idx).to_numpy()
        a_idx = df["AwayTeam"].map(idx).to_numpy()
        hg = df["FTHG"].to_numpy().astype(int)
        ag = df["FTAG"].to_numpy().astype(int)

        def unpack(p):
            atk = p[:n]
            dfn = p[n:2 * n]
            gamma = p[2 * n]
            l3 = p[2 * n + 1]
            return atk - atk.mean(), dfn, gamma, l3

        def neg_ll(p):
            atk, dfn, gamma, l3 = unpack(p)
            l1 = np.exp(atk[h_idx] - dfn[a_idx] + gamma)
            l2 = np.exp(atk[a_idx] - dfn[h_idx])
            ll = 0.0
            for x, y, a, b, w in zip(hg, ag, l1, l2, weights):
                ll += w * math.log(max(_biv_pmf(int(x), int(y), float(a), float(b), l3), 1e-12))
            return -ll

        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25], [0.1]])
        res = minimize(neg_ll, x0, method="L-BFGS-B",
                       bounds=[(-3, 3)] * (2 * n) + [(-1, 2), (1e-6, 1.0)])
        atk, dfn, gamma, l3 = unpack(res.x)
        self.attack = {t: float(atk[i]) for t, i in idx.items()}
        self.defense = {t: float(dfn[i]) for t, i in idx.items()}
        self.gamma = float(gamma)
        self.lambda3 = float(l3)

    def score_matrix(self, home: str, away: str) -> np.ndarray:
        if home not in self.attack:
            raise KeyError(home)
        if away not in self.attack:
            raise KeyError(away)
        l1 = math.exp(self.attack[home] - self.defense[away] + self.gamma)
        l2 = math.exp(self.attack[away] - self.defense[home])
        g = self.max_goals + 1
        M = np.array([[_biv_pmf(i, j, l1, l2, self.lambda3) for j in range(g)]
                      for i in range(g)], dtype=float)
        return normalize(M)
