"""Dixon-Coles goals model.

Parameters: per-team attack (alpha) and defense (beta), global home advantage
(gamma), and low-score correction (rho). Fit by maximizing the time-decay-weighted
log-likelihood over historical matches.

History DataFrame columns (football-data.co.uk format):
  Date, HomeTeam, AwayTeam, FTHG (full-time home goals), FTAG (full-time away goals).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from .base import BaseModel
from .markets import normalize

def _tau(x: int, y: int, lh: float, la: float, rho: float) -> float:
    """Dixon-Coles low-score correction on the four cells (0,0),(0,1),(1,0),(1,1)."""
    if x == 0 and y == 0:
        return 1.0 - lh * la * rho
    if x == 0 and y == 1:
        return 1.0 + lh * rho
    if x == 1 and y == 0:
        return 1.0 + la * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0

class DixonColesModel(BaseModel):
    def __init__(self, max_goals: int = 10, xi: float = 0.0018) -> None:
        self.max_goals = max_goals
        self.xi = xi
        self.teams: list[str] = []
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.gamma: float = 0.0
        self.rho: float = 0.0

    def fit(self, history: pd.DataFrame) -> None:
        df = history.copy()
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
        self.teams = teams
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        # time-decay weights
        tmax = df["Date"].max()
        weights = np.exp(-self.xi * (tmax - df["Date"]).dt.days.to_numpy())

        h_idx = df["HomeTeam"].map(idx).to_numpy()
        a_idx = df["AwayTeam"].map(idx).to_numpy()
        hg = df["FTHG"].to_numpy().astype(int)
        ag = df["FTAG"].to_numpy().astype(int)

        # params: attack[n], defense[n], gamma, rho. Constrain mean(attack)=0 via offset.
        def unpack(p):
            atk = p[:n]; dfn = p[n:2 * n]; gamma = p[2 * n]; rho = p[2 * n + 1]
            atk = atk - atk.mean()  # identifiability
            return atk, dfn, gamma, rho

        def neg_ll(p):
            atk, dfn, gamma, rho = unpack(p)
            lh = np.exp(atk[h_idx] - dfn[a_idx] + gamma)
            la = np.exp(atk[a_idx] - dfn[h_idx])
            ll = (poisson.logpmf(hg, lh) + poisson.logpmf(ag, la))
            tau = np.array([np.log(max(_tau(int(x), int(y), float(l1), float(l2), rho), 1e-10))
                            for x, y, l1, l2 in zip(hg, ag, lh, la)])
            return -np.sum(weights * (ll + tau))

        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25], [-0.05]])
        res = minimize(neg_ll, x0, method="L-BFGS-B",
                       bounds=[(-3, 3)] * (2 * n) + [(-1, 2), (-0.2, 0.2)])
        atk, dfn, gamma, rho = unpack(res.x)
        self.attack = {t: float(atk[i]) for t, i in idx.items()}
        self.defense = {t: float(dfn[i]) for t, i in idx.items()}
        self.gamma = float(gamma)
        self.rho = float(rho)

    def score_matrix(self, home: str, away: str) -> np.ndarray:
        if home not in self.attack:
            raise KeyError(home)
        if away not in self.attack:
            raise KeyError(away)
        lh = np.exp(self.attack[home] - self.defense[away] + self.gamma)
        la = np.exp(self.attack[away] - self.defense[home])
        g = self.max_goals + 1
        home_p = poisson.pmf(np.arange(g), lh)
        away_p = poisson.pmf(np.arange(g), la)
        M = np.outer(home_p, away_p)
        for x in range(min(2, g)):
            for y in range(min(2, g)):
                M[x, y] *= _tau(x, y, lh, la, self.rho)
        return normalize(M)
