"""xG-based goals model: fit team strengths on expected goals (xG) instead of scorelines.

Shot quality (xG) predicts future results better than actual goals, which are noisy (a deflected
30-yard screamer counts the same as a tap-in). When the history carries xG columns this model
fits attack/defense to expected goals via a quasi-Poisson deviance (continuous-response friendly),
then predicts the goal distribution with those xG-based rates. Falls back to actual goals (FTHG/
FTAG) when no xG columns are present, so it is always usable.

Recognised xG column name pairs (home, away): HxG/AxG, xGH/xGA, Home_xG/Away_xG.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from .base import BaseModel
from .markets import normalize

_XG_PAIRS = [("HxG", "AxG"), ("xGH", "xGA"), ("Home_xG", "Away_xG")]


def _xg_columns(df: pd.DataFrame):
    for h, a in _XG_PAIRS:
        if h in df.columns and a in df.columns:
            return h, a
    return None


class XGDixonColesModel(BaseModel):
    def __init__(self, max_goals: int = 10, xi: float = 0.0018) -> None:
        self.max_goals = max_goals
        self.xi = xi
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.gamma: float = 0.0
        self.fit_on_xg = False

    def fit(self, history: pd.DataFrame) -> None:
        df = history.copy()
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        cols = _xg_columns(df)
        self.fit_on_xg = cols is not None
        if cols:
            df = df.dropna(subset=list(cols))
            hx = df[cols[0]].to_numpy(dtype=float)
            ax = df[cols[1]].to_numpy(dtype=float)
        else:
            hx = df["FTHG"].to_numpy(dtype=float)
            ax = df["FTAG"].to_numpy(dtype=float)

        teams = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        tmax = df["Date"].max()
        weights = np.exp(-self.xi * (tmax - df["Date"]).dt.days.to_numpy())
        h_idx = df["HomeTeam"].map(idx).to_numpy()
        a_idx = df["AwayTeam"].map(idx).to_numpy()

        def unpack(p):
            atk = p[:n]
            return atk - atk.mean(), p[n:2 * n], p[2 * n]

        def neg_dev(p):
            # quasi-Poisson deviance (drops the x! constant -> works for continuous xG).
            atk, dfn, gamma = unpack(p)
            lh = np.exp(atk[h_idx] - dfn[a_idx] + gamma)
            la = np.exp(atk[a_idx] - dfn[h_idx])
            dev = (lh - hx * np.log(lh)) + (la - ax * np.log(la))
            return np.sum(weights * dev)

        x0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25]])
        res = minimize(neg_dev, x0, method="L-BFGS-B",
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
        g = self.max_goals + 1
        return normalize(np.outer(poisson.pmf(np.arange(g), lh),
                                  poisson.pmf(np.arange(g), la)))
