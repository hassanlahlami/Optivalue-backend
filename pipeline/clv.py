"""Closing Line Value: record closing odds, then score each bet against the close.

CLV is the honesty metric. clv_price > 0 means we took a better price than the close.
Reliability flag stays False until we have >= settings.clv_reliable_min settled bets.
"""
from __future__ import annotations
import datetime as dt
import logging
import statistics
from pipeline.devig import implied_prob
from storage.repositories import OddsRepo, BetRepo, ClvRepo

log = logging.getLogger(__name__)

def record_closing(odds_client, conn, settings, date) -> int:
    odds = odds_client.fetch_odds([lg.key for lg in settings.leagues])
    repo = OddsRepo(conn)
    now = dt.datetime.utcnow().isoformat()
    count = 0
    for o in odds:
        if date and not o.kickoff_utc.startswith(date):
            continue
        repo.insert_snapshot({"match_id": o.match_id, "market": o.market,
            "selection": o.selection, "line": o.line, "book": o.book,
            "decimal_odds": o.decimal_odds, "captured_at": now,
            "snapshot_type": "closing"})
        count += 1
    return count

def compute_clv(conn, settings) -> dict:
    bet_repo, odds_repo, clv_repo = BetRepo(conn), OddsRepo(conn), ClvRepo(conn)
    now = dt.datetime.utcnow().isoformat()
    clv_prices: list[float] = []
    clv_probs: list[float] = []
    by_league: dict[str, list[float]] = {}
    by_market: dict[str, list[float]] = {}

    for bet in bet_repo.list():
        closing = odds_repo.closing_for(bet["match_id"], bet["market"],
                                        bet["selection"], bet["line"])
        if closing is None:
            continue
        clv_price = bet["taken_odds"] / closing - 1.0
        closing_fair = implied_prob(closing)  # single-leg approximation of fair close
        clv_prob = closing_fair - bet["fair_prob"]
        clv_repo.upsert({"bet_id": bet["bet_id"], "closing_odds": closing,
            "closing_fair_prob": closing_fair, "clv_price": clv_price,
            "clv_prob": clv_prob, "settled_at": now})
        if bet["status"] == "open":
            bet_repo.set_status(bet["bet_id"], "closed")
        clv_prices.append(clv_price)
        clv_probs.append(clv_prob)
        by_league.setdefault(bet["league"], []).append(clv_price)
        by_market.setdefault(bet["market"], []).append(clv_price)

    n = len(clv_prices)
    pct_pos = 100.0 * sum(1 for c in clv_prices if c > 0) / n if n else 0.0
    mean_price = statistics.fmean(clv_prices) if clv_prices else 0.0

    # 95% confidence interval on mean CLV (normal approx). "Significant" = the whole interval
    # is above zero AND we have a usable sample — i.e., we are beating the close beyond noise.
    ci_low = ci_high = 0.0
    significant = False
    if n >= 2:
        se = statistics.stdev(clv_prices) / (n ** 0.5)
        ci_low, ci_high = mean_price - 1.96 * se, mean_price + 1.96 * se
        significant = bool(ci_low > 0.0 and n >= settings.clv_reliable_min)

    return {
        "sample_size": n,
        "pct_positive_clv": pct_pos,
        "mean_clv_price": mean_price,
        "mean_clv_prob": statistics.fmean(clv_probs) if clv_probs else 0.0,
        "clv_price_ci_low": ci_low,
        "clv_price_ci_high": ci_high,
        "significant": significant,
        "reliable": n >= settings.clv_reliable_min,
        "by_league": {k: statistics.fmean(v) for k, v in by_league.items()},
        "by_market": {k: statistics.fmean(v) for k, v in by_market.items()},
    }
