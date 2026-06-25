"""Negative-binomial corners model — corners are overdispersed relative to Poisson.

The Poisson corners model assumes variance = mean, but corner counts vary more than that
(blowouts, game state, tactics). The negative binomial adds a dispersion parameter r and
approaches Poisson as r -> infinity, so it fits the heavier tails better. Same per-team
attack/defense + home-advantage mean structure as the Poisson version; swap via settings.corners_model.

History columns: Date, HomeTeam, AwayTeam, HC, AC.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom
from .base import BaseModel
from .markets import normalize


def _nb_p(mu: np.ndarray | float, r: float):
    """Convert mean mu + dispersion r to the nbinom success prob (mean stays mu)."""
    return r / (r + mu)


class CornersNegBinModel(BaseModel):
    def __init__(self, max_corners: int = 20, xi: float = 0.0018) -> None:
        self.max_corners = max_corners
        self.xi = xi
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.gamma: float = 0.0
        self.r: float = 10.0  # dispersion (large -> Poisson)

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
            atk = p[:n]
            return atk - atk.mean(), p[n:2 * n], p[2 * n], np.exp(p[2 * n + 1])

        def neg_ll(p):
            atk, dfn, gamma, r = unpack(p)
            lh = np.exp(atk[h_idx] - dfn[a_idx] + gamma)
            la = np.exp(atk[a_idx] - dfn[h_idx])
            ll = (nbinom.logpmf(hc, r, _nb_p(lh, r))
                  + nbinom.logpmf(ac, r, _nb_p(la, r)))
            return -np.sum(weights * ll)

        # last param is log(r); bound r within [~1, ~500].
        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.1], [np.log(10.0)]])
        res = minimize(neg_ll, x0, method="L-BFGS-B",
                       bounds=[(-3, 3)] * (2 * n) + [(-1, 2), (0.0, 6.2)])
        atk, dfn, gamma, r = unpack(res.x)
        self.attack = {t: float(atk[i]) for t, i in idx.items()}
        self.defense = {t: float(dfn[i]) for t, i in idx.items()}
        self.gamma = float(gamma)
        self.r = float(r)

    def score_matrix(self, home: str, away: str) -> np.ndarray:
        if home not in self.attack:
            raise KeyError(home)
        if away not in self.attack:
            raise KeyError(away)
        lh = np.exp(self.attack[home] - self.defense[away] + self.gamma)
        la = np.exp(self.attack[away] - self.defense[home])
        c = self.max_corners + 1
        ks = np.arange(c)
        home_p = nbinom.pmf(ks, self.r, _nb_p(lh, self.r))
        away_p = nbinom.pmf(ks, self.r, _nb_p(la, self.r))
        return normalize(np.outer(home_p, away_p))
