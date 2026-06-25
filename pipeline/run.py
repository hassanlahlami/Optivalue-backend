"""Daily pipeline: fetch odds -> model probs -> de-vig market -> edge/EV -> filter -> store.

Selections are grouped by (match, market, line) so a market's outcomes can be de-vigged
together and line-shopped across books. Single selections only.
"""
from __future__ import annotations
import collections
import datetime as dt
import logging
from dataclasses import dataclass, field
import pandas as pd
from pipeline.devig import devig
from pipeline.ev import best_price, edge, expected_value, kelly_stake, passes
from pipeline.explain import build_explainer
from model.dixon_coles import DixonColesModel
from model.corners import CornersPoissonModel
from model.blend import blend_probs
from model.calibrate import IsotonicCalibrator
from model.registry import build_goals, build_corners
from model import markets as mk
from storage.repositories import MatchRepo, OddsRepo, BetRepo

log = logging.getLogger(__name__)


def _match_outcome(hg: int, ag: int) -> str:
    return "home" if hg > ag else "away" if ag > hg else "draw"


def _fit_goals_calibrator(history: pd.DataFrame, settings):
    """Fit an isotonic calibrator on a holdout of 1X2 predictions (pooled over outcomes).

    Returns None unless calibration is enabled and there are enough held-out points — never
    calibrate on data too thin to be meaningful.
    """
    if not settings.calibrate_enabled:
        return None
    df = history.copy()
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]).sort_values("Date")
    n = len(df)
    cut = int(n * 0.7)
    if n - cut < 1:
        return None
    train, test = df.iloc[:cut], df.iloc[cut:]
    model = build_goals(settings.goals_model, settings)
    model.fit(train)
    probs, hits = [], []
    for _, r in test.iterrows():
        try:
            M = model.score_matrix(r["HomeTeam"], r["AwayTeam"])
        except KeyError:
            continue
        p = mk.one_x_two(M)
        outcome = _match_outcome(int(r["FTHG"]), int(r["FTAG"]))
        for k in ("home", "draw", "away"):
            probs.append(p[k])
            hits.append(1.0 if outcome == k else 0.0)
    if len(probs) < settings.calibrate_min_samples:
        return None
    return IsotonicCalibrator().fit(probs, hits)


def _calibrate(dist: dict, calibrator) -> dict:
    if calibrator is None:
        return dist
    cal = {k: float(calibrator.transform([v])[0]) for k, v in dist.items()}
    total = sum(cal.values())
    return {k: v / total for k, v in cal.items()} if total > 0 else dist


@dataclass
class ModelBundle:
    # One fitted model per model_group (e.g. "club", "international"). Club and national
    # teams are disjoint populations, so they must not share a fit.
    goals: dict[str, DixonColesModel]
    corners: dict[str, CornersPoissonModel]
    # Optional isotonic calibrator per group (only present when fit on enough data).
    calibrators: dict[str, object] = field(default_factory=dict)

def fit_models(results_client, settings) -> ModelBundle:
    # Group each league's history by its model_group, then fit one model per group.
    frames_by_group: dict[str, list] = collections.defaultdict(list)
    for lg in settings.leagues:
        try:
            frames_by_group[lg.model_group].append(results_client.fetch_history(lg.history_code))
        except Exception as exc:  # noqa: BLE001
            log.error("history fetch failed for %s: %s", lg.history_code, exc)

    goals: dict[str, DixonColesModel] = {}
    corners: dict[str, CornersPoissonModel] = {}
    calibrators: dict[str, object] = {}
    for group, frames in frames_by_group.items():
        history = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if history.empty:
            continue
        g = build_goals(settings.goals_model, settings)
        g.fit(history)
        # International fixtures (World Cup) are mostly neutral-venue: a venue-aware model
        # should predict with home advantage switched off for that group.
        if group == "international" and hasattr(g, "default_neutral"):
            g.default_neutral = True
        goals[group] = g
        cal = _fit_goals_calibrator(history, settings)
        if cal is not None:
            calibrators[group] = cal
        # Corners only where the source carries corner counts (club leagues); the
        # international group has no HC/AC, so corner markets are auto-disabled there.
        if {"HC", "AC"} <= set(history.columns):
            c = build_corners(settings.corners_model, settings)
            c.fit(history)
            corners[group] = c
    return ModelBundle(goals=goals, corners=corners, calibrators=calibrators)

def model_prob_for(bundle, group, home, away, market, selection, line, settings) -> float | None:
    goals = bundle.goals.get(group)
    if goals is None:
        return None  # no fitted model for this league's group
    try:
        if market == "h2h":
            M = goals.score_matrix(home, away)
            r = mk.one_x_two(M)
            if selection == home:
                return r["home"]
            if selection == away:
                return r["away"]
            if selection.lower() == "draw":
                return r["draw"]
            return None
        if market == "totals_goals":
            M = goals.score_matrix(home, away)
            r = mk.over_under_total(M, float(line))
            return r["over"] if selection.lower() == "over" else r["under"]
        if market == "totals_corners":
            corners = bundle.corners.get(group)
            if corners is None or not corners.attack:
                return None
            M = corners.score_matrix(home, away)
            r = mk.over_under_total(M, float(line))
            return r["over"] if selection.lower() == "over" else r["under"]
    except KeyError:
        return None  # team not in training set
    return None

def _line_allowed(market: str, line, settings) -> bool:
    """Keep only the totals lines configured in settings; h2h (line is None) is always allowed."""
    if market == "totals_goals":
        return line is not None and float(line) in settings.goals_lines
    if market == "totals_corners":
        return line is not None and float(line) in settings.corners_lines
    return True


def _consensus_fair_for(market_books: dict, sel_list: list[str], best: dict, settings) -> dict[str, float]:
    """Combine per-book de-vigged fair probabilities into one fair prob per selection.

    De-vig removes each book's margin *within that book's own market*, so the outcomes
    used for de-vig are mutually exclusive and consistent. We then combine across books:
      - consensus == "average" (default): mean of the per-book fair probs.
      - consensus == "best": the fair prob from the book offering the best price we'd take.
    Falls back to de-vigging the best-price composite if no single book quotes the full
    set of outcomes (de-vig is only valid over a complete market).

    market_books: {book: {selection: decimal_odds}} for one (match, market, line).
    best:         {selection: (book, best_decimal_odds)} from line shopping.
    """
    per_book: dict[str, list[tuple[str, float]]] = {s: [] for s in sel_list}
    for book, quotes in market_books.items():
        if set(sel_list) <= set(quotes):  # only de-vig books covering the full market
            probs = devig([quotes[s] for s in sel_list], method=settings.devig_method)
            for s, p in zip(sel_list, probs):
                per_book[s].append((book, p))

    if not any(per_book[s] for s in sel_list):
        probs = devig([best[s][1] for s in sel_list], method=settings.devig_method)
        return dict(zip(sel_list, probs))

    fair_map: dict[str, float] = {}
    for s in sel_list:
        entries = per_book[s]
        if not entries:                       # this selection missing from full-coverage books
            fair_map[s] = 1.0 / best[s][1]
        elif settings.consensus == "best":
            match = [p for bk, p in entries if bk == best[s][0]]
            fair_map[s] = match[0] if match else sum(p for _, p in entries) / len(entries)
        else:                                 # average across books (default)
            fair_map[s] = sum(p for _, p in entries) / len(entries)
    return fair_map


def run_daily(odds_client, bundle, conn, settings, date: str) -> list[dict]:
    odds = odds_client.fetch_odds([lg.key for lg in settings.leagues])
    group_by_league = {lg.key: lg.model_group for lg in settings.leagues}
    by_outcome = collections.defaultdict(list)   # (match,market,sel,line) -> [(book,odds)]
    by_market = collections.defaultdict(set)     # (match,market,line) -> {selection}
    by_book = collections.defaultdict(dict)      # (match,market,line) -> {book: {sel: odds}}
    meta = {}
    for o in odds:
        if date and not o.kickoff_utc.startswith(date):
            continue
        if not _line_allowed(o.market, o.line, settings):
            continue
        by_outcome[(o.match_id, o.market, o.selection, o.line)].append((o.book, o.decimal_odds))
        by_market[(o.match_id, o.market, o.line)].add(o.selection)
        by_book[(o.match_id, o.market, o.line)].setdefault(o.book, {})[o.selection] = o.decimal_odds
        meta[o.match_id] = o

    match_repo, odds_repo, bet_repo = MatchRepo(conn), OddsRepo(conn), BetRepo(conn)
    explainer = build_explainer(settings)
    now = dt.datetime.utcnow().isoformat()
    flagged: list[dict] = []

    for (match_id, market, line), selections in by_market.items():
        m = meta[match_id]
        match_repo.upsert({"match_id": match_id, "league": m.league, "home": m.home,
                           "away": m.away, "kickoff_utc": m.kickoff_utc,
                           "status": "scheduled"})
        sel_list = sorted(selections)
        best = {}
        for sel in sel_list:
            book, price = best_price(by_outcome[(match_id, market, sel, line)])
            best[sel] = (book, price)
        fair_map = _consensus_fair_for(by_book[(match_id, market, line)], sel_list, best, settings)

        # Final probability = model blended toward the de-vigged market (the backtest-proven
        # edge improvement). Only blend when the model can price the whole market; otherwise
        # fall back to raw model probs per selection.
        group = group_by_league.get(m.league, "club")
        model_dist = {sel: model_prob_for(bundle, group, m.home, m.away, market, sel, line, settings)
                      for sel in sel_list}
        blended = None
        if all(v is not None for v in model_dist.values()):
            blended = blend_probs(model_dist, {s: fair_map[s] for s in sel_list},
                                  settings.blend_weight)
            # Calibration was fit on 1X2 predictions, so only apply it to the h2h market.
            if market == "h2h":
                blended = _calibrate(blended, bundle.calibrators.get(group))

        for sel in sel_list:
            book, price = best[sel]
            odds_repo.insert_snapshot({"match_id": match_id, "market": market,
                "selection": sel, "line": line, "book": book, "decimal_odds": price,
                "captured_at": now, "snapshot_type": "current"})
            mp = blended[sel] if blended is not None else model_dist[sel]
            if mp is None:
                continue
            ev = expected_value(mp, price)
            if not passes(ev, settings.ev_threshold):
                continue
            stake = kelly_stake(mp, price, settings.kelly_fraction, settings.flat_stake)
            bet = {"timestamp": now, "match_id": match_id, "league": m.league,
                   "market": market, "selection": sel, "line": line,
                   "model_prob": mp, "fair_prob": fair_map[sel],
                   "edge": edge(mp, fair_map[sel]), "ev": ev, "taken_odds": price,
                   "book": book, "stake": stake, "status": "open"}
            record = {**bet, "home": m.home, "away": m.away, "best_odds": price}
            bet["explanation"] = explainer.explain(record)
            record["explanation"] = bet["explanation"]
            bet_repo.insert(bet)
            flagged.append(record)

    flagged.sort(key=lambda b: b["ev"], reverse=True)
    return flagged
