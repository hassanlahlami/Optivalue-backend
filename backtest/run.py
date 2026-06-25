"""Holdout backtest: fit the goals model on the earliest train_frac of matches, then score
1X2 predictions on the held-out remainder. Compares the model against a base-rate baseline so
you can see whether it adds anything over "just predict how often home/draw/away happens".

This is the offline truth machine. Out-of-sample only — no look-ahead. (CLV/ROI backtest against
historical closing odds is a documented follow-up that needs odds-bearing CSVs.)
"""
from __future__ import annotations
import pandas as pd
from model.dixon_coles import DixonColesModel
from model import markets as mk
from backtest.metrics import (
    brier_score, log_loss, calibration_table, expected_calibration_error,
)


def _outcome(hg: int, ag: int) -> str:
    return "home" if hg > ag else "away" if ag > hg else "draw"


def holdout_backtest(history: pd.DataFrame, settings, train_frac: float = 0.7) -> dict:
    df = history.copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]).sort_values("Date")
    n = len(df)
    if n < 4:
        return {"sample_size": 0, "skipped": 0, "note": "not enough history to backtest"}

    cut = max(1, int(n * train_frac))
    train, test = df.iloc[:cut], df.iloc[cut:]

    model = DixonColesModel(max_goals=settings.max_goals, xi=settings.time_decay_xi)
    model.fit(train)

    # NAIVE base-rate baseline from the training split.
    thg = train["FTHG"].astype(int)
    tag = train["FTAG"].astype(int)
    base = {"home": float((thg > tag).mean()), "away": float((tag > thg).mean())}
    base["draw"] = 1.0 - base["home"] - base["away"]

    preds: list[dict] = []
    outcomes: list[str] = []
    home_probs: list[float] = []
    home_hits: list[float] = []
    skipped = 0
    for _, r in test.iterrows():
        try:
            M = model.score_matrix(r["HomeTeam"], r["AwayTeam"])
        except KeyError:
            skipped += 1
            continue
        p = mk.one_x_two(M)
        y = _outcome(int(r["FTHG"]), int(r["FTAG"]))
        preds.append(p)
        outcomes.append(y)
        home_probs.append(p["home"])
        home_hits.append(1.0 if y == "home" else 0.0)

    if not preds:
        return {"sample_size": 0, "skipped": skipped,
                "note": "no testable matches (test teams unseen in training split)"}

    return {
        "sample_size": len(preds),
        "skipped": skipped,
        "brier": brier_score(preds, outcomes),
        "baseline_brier": brier_score([base] * len(outcomes), outcomes),
        "log_loss": log_loss(preds, outcomes),
        "ece_home": expected_calibration_error(home_probs, home_hits, bins=10),
        "calibration_home": calibration_table(home_probs, home_hits, bins=10),
    }
