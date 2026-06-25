"""CLV / ROI backtest against historical bookmaker odds — the real edge metric.

football-data.co.uk CSVs carry Pinnacle prices: PSH/PSD/PSA (taken earlier) and
PSCH/PSCD/PSCA (closing). We fit the goals model on the training split, then on the
held-out test split we flag the model's +EV selections at the TAKEN price and measure:
  - CLV:  did the taken price beat the closing price?  clv_price = taken/closing - 1
  - ROI:  settle each flagged bet by the actual result at the taken price (1u stakes).

Blending the model toward the de-vigged market by weight w usually improves CLV;
`tune_blend_weight` scans w and returns the one with the best mean CLV. Out-of-sample only.
"""
from __future__ import annotations
import pandas as pd
from model.dixon_coles import DixonColesModel
from model import markets as mk
from model.blend import blend_probs
from pipeline.devig import devig

ODDS_COLS = ["PSH", "PSD", "PSA", "PSCH", "PSCD", "PSCA"]
_SEL = ("home", "draw", "away")


def _outcome(hg: int, ag: int) -> str:
    return "home" if hg > ag else "away" if ag > hg else "draw"


def _prep(history: pd.DataFrame) -> pd.DataFrame:
    df = history.copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    return df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]).sort_values("Date")


def clv_backtest(history: pd.DataFrame, settings, train_frac: float = 0.7, w: float = 0.5) -> dict:
    df = _prep(history)
    if not set(ODDS_COLS) <= set(df.columns):
        return {"n": 0, "note": "history has no Pinnacle PS*/PSC* odds columns", "w": w}
    df = df.dropna(subset=ODDS_COLS)
    n = len(df)
    if n < 4:
        return {"n": 0, "note": "not enough priced history to backtest", "w": w}
    cut = max(1, int(n * train_frac))
    flagged = _eval_block(df.iloc[:cut], df.iloc[cut:], settings, w)
    return _summarize(flagged, w)


def _eval_block(train: pd.DataFrame, test: pd.DataFrame, settings, w: float) -> list[dict]:
    """Fit on `train`, flag the model's +EV selections on `test` at the taken price."""
    model = DixonColesModel(max_goals=settings.max_goals, xi=settings.time_decay_xi)
    model.fit(train)
    flagged: list[dict] = []
    for _, r in test.iterrows():
        try:
            M = model.score_matrix(r["HomeTeam"], r["AwayTeam"])
        except KeyError:
            continue
        taken = {"home": float(r["PSH"]), "draw": float(r["PSD"]), "away": float(r["PSA"])}
        closing = {"home": float(r["PSCH"]), "draw": float(r["PSCD"]), "away": float(r["PSCA"])}
        if any(v <= 1.0 for v in (*taken.values(), *closing.values())):
            continue
        model_p = mk.one_x_two(M)
        market_fair = dict(zip(_SEL, devig([taken[s] for s in _SEL], method=settings.devig_method)))
        blended = blend_probs(model_p, market_fair, w)
        outcome = _outcome(int(r["FTHG"]), int(r["FTAG"]))
        for s in _SEL:
            ev = blended[s] * taken[s] - 1.0
            if ev <= settings.ev_threshold:
                continue
            won = s == outcome
            flagged.append({
                "clv_price": taken[s] / closing[s] - 1.0,
                "profit": (taken[s] - 1.0) if won else -1.0,
            })
    return flagged


def _summarize(flagged: list[dict], w: float, **extra) -> dict:
    k = len(flagged)
    if k == 0:
        return {"n": 0, "note": "model flagged no +EV bets on the test split", "w": w, **extra}
    return {
        "n": k,
        "w": w,
        "roi": sum(f["profit"] for f in flagged) / k,
        "pct_beat_close": 100.0 * sum(1 for f in flagged if f["clv_price"] > 0) / k,
        "mean_clv": sum(f["clv_price"] for f in flagged) / k,
        **extra,
    }


def walk_forward_clv(history: pd.DataFrame, settings, folds: int = 4, w: float = 0.5) -> dict:
    """Expanding-origin walk-forward: each fold trains on all data before its test block, so
    every test prediction is strictly out-of-sample. More honest than a single holdout split.
    """
    df = _prep(history)
    if not set(ODDS_COLS) <= set(df.columns):
        return {"n": 0, "note": "history has no Pinnacle PS*/PSC* odds columns", "w": w, "folds": folds}
    df = df.dropna(subset=ODDS_COLS).reset_index(drop=True)
    n = len(df)
    if n < folds + 2:
        return {"n": 0, "note": "not enough priced history for walk-forward", "w": w, "folds": folds}
    bounds = [int(n * (i + 1) / (folds + 1)) for i in range(folds + 1)]
    flagged: list[dict] = []
    for i in range(folds):
        a, b = bounds[i], bounds[i + 1]
        if a < 1 or b <= a:
            continue
        flagged.extend(_eval_block(df.iloc[:a], df.iloc[a:b], settings, w))
    return _summarize(flagged, w, folds=folds)


def tune_blend_weight(history: pd.DataFrame, settings, train_frac: float = 0.7,
                      weights=(0.0, 0.25, 0.5, 0.75, 1.0)) -> dict:
    """Scan blend weights; return the one with the best mean CLV plus all results."""
    runs = [clv_backtest(history, settings, train_frac, w) for w in weights]
    scored = [r for r in runs if r.get("n", 0) > 0]
    best = max(scored, key=lambda r: r["mean_clv"]) if scored else None
    return {"best": best, "all": runs}
