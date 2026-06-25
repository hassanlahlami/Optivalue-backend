"""Team-strength corners model.

# NAIVE: Same attack/defense/home-advantage Poisson structure as the goals model,
# but fit on corner counts (HC/AC). No Dixon-Coles rho correction — that adjusts the
# low-score GOAL cells (0-0/1-0/1-1) and has no meaning for corners. Corner data is
# also noisier and sparser than goals; treat these probabilities as the weakest link
# and improve here first (e.g. negative-binomial for overdispersion).

History DataFrame columns (football-data.co.uk): Date, HomeTeam, AwayTeam, HC, AC.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from .base import BaseModel
from .markets import normalize

class CornersPoissonModel(BaseModel):
    def __init__(self, max_corners: int = 20, xi: float = 0.0018) -> None:
        self.max_corners = max_corners
        self.xi = xi
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.gamma: float = 0.0

    def fit(self, history: pd.DataFrame) -> None:
        df = history.copy()
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "HC", "AC"])
        teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        tmax = df["Date"].max()
        weights = np.exp(-self.xi * (tmax - df["Date"]).dt.days.to_numpy())
        h_idx = df["HomeTeam"].map(idx).to_numpy()
        a_idx = df["AwayTeam"].map(idx).to_numpy()
        hc = df["HC"].to_numpy().astype(int)
        ac = df["AC"].to_numpy().astype(int)

        def unpack(p):
            atk = p[:n]; dfn = p[n:2 * n]; gamma = p[2 * n]
            return atk - atk.mean(), dfn, gamma

        def neg_ll(p):
            atk, dfn, gamma = unpack(p)
            lh = np.exp(atk[h_idx] - dfn[a_idx] + gamma)
            la = np.exp(atk[a_idx] - dfn[h_idx])
            ll = poisson.logpmf(hc, lh) + poisson.logpmf(ac, la)
            return -np.sum(weights * ll)

        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.1]])
        res = minimize(neg_ll, x0, method="L-BFGS-B",
                       bounds=[(-3, 3)] * (2 * n) + [(-1, 2)])
        atk, dfn, gamma = unpack(res.x)
        self.attack = {t: float(atk[i]) for t, i in idx.items()}
        self.defense = {t: float(dfn[i]) for t, i in idx.items()}
        self.gamma = float(gamma)

    def score_matrix(self, home: str, away: str) -> np.ndarray:
        if home not in self.attack:
            raise KeyError(home)
        if away not in self.attack:
            raise KeyError(away)
        lh = np.exp(self.attack[home] - self.defense[away] + self.gamma)
        la = np.exp(self.attack[away] - self.defense[home])
        c = self.max_corners + 1
        home_p = poisson.pmf(np.arange(c), lh)
        away_p = poisson.pmf(np.arange(c), la)
        return normalize(np.outer(home_p, away_p))
