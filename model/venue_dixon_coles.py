"""Venue-aware Dixon-Coles goals model.

Standard Dixon-Coles applies one global home-advantage term to whichever side is labelled
"home". That is wrong for neutral-venue games (most World Cup matches), where there is no real
home edge. This variant:
  - estimates gamma using ONLY non-neutral historical matches (the `neutral` column gates it), and
  - at prediction time applies gamma only when the fixture is not neutral (default_neutral flag).
The pipeline sets default_neutral=True for the international model group, so World Cup matches no
longer get a spurious home edge. On club data (no `neutral` column) it behaves like normal DC.

History columns: Date, HomeTeam, AwayTeam, FTHG, FTAG, and optional `neutral` (bool/TRUE-FALSE).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from .base import BaseModel
from .markets import normalize
from .dixon_coles import _tau


def _neutral_array(df: pd.DataFrame) -> np.ndarray:
    if "neutral" not in df.columns:
        return np.zeros(len(df), dtype=bool)
    return df["neutral"].map(
        lambda v: str(v).strip().lower() in ("true", "1", "yes")).to_numpy(dtype=bool)


class VenueAwareDixonColesModel(BaseModel):
    def __init__(self, max_goals: int = 10, xi: float = 0.0018, default_neutral: bool = False) -> None:
        self.max_goals = max_goals
        self.xi = xi
        self.default_neutral = default_neutral
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.gamma: float = 0.0
        self.rho: float = 0.0

    def fit(self, history: pd.DataFrame) -> None:
        df = history.copy()
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        home_active = (~_neutral_array(df)).astype(float)  # 1 if a real home game, else 0
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
            return atk - atk.mean(), dfn, p[2 * n], p[2 * n + 1]

        def neg_ll(p):
            atk, dfn, gamma, rho = unpack(p)
            lh = np.exp(atk[h_idx] - dfn[a_idx] + gamma * home_active)
            la = np.exp(atk[a_idx] - dfn[h_idx])
            ll = poisson.logpmf(hg, lh) + poisson.logpmf(ag, la)
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
        active = 0.0 if self.default_neutral else 1.0
        lh = np.exp(self.attack[home] - self.defense[away] + self.gamma * active)
        la = np.exp(self.attack[away] - self.defense[home])
        g = self.max_goals + 1
        M = np.outer(poisson.pmf(np.arange(g), lh), poisson.pmf(np.arange(g), la))
        for x in range(min(2, g)):
            for y in range(min(2, g)):
                M[x, y] *= _tau(x, y, lh, la, self.rho)
        return normalize(M)
