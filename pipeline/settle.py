"""Settle bets by actual match results: grade win/loss/void and compute realized P/L.

P/L is reported as SECONDARY to CLV — it is high-variance and a small sample proves little.
CLV is the real edge test; settlement just tracks what actually happened.
"""
from __future__ import annotations
import datetime as dt
import pandas as pd
from storage.repositories import BetRepo, SettlementRepo


def grade_bet(bet: dict, result: dict) -> tuple[str, float]:
    """Grade a 1-unit stake. Returns (grade, profit) with grade in {win, loss, void}.

    bet needs: market, selection, line, taken_odds, home, away.
    result needs: home_goals, away_goals (+ home_corners, away_corners for corner markets).
    """
    market = bet["market"]
    sel = bet["selection"]
    line = bet.get("line")
    odds = bet["taken_odds"]
    hg, ag = result["home_goals"], result["away_goals"]

    if market == "h2h":
        outcome = "home" if hg > ag else "away" if ag > hg else "draw"
        won = ((sel == bet.get("home") and outcome == "home")
               or (sel == bet.get("away") and outcome == "away")
               or (sel.lower() == "draw" and outcome == "draw"))
        return ("win", odds - 1.0) if won else ("loss", -1.0)

    if market in ("totals_goals", "totals_corners"):
        if line is None:
            return ("void", 0.0)
        if market == "totals_goals":
            total = hg + ag
        else:
            total = result.get("home_corners", 0) + result.get("away_corners", 0)
        if total == line:  # exact whole-number line = push
            return ("void", 0.0)
        over = total > line
        won = (sel.lower() == "over" and over) or (sel.lower() == "under" and not over)
        return ("win", odds - 1.0) if won else ("loss", -1.0)

    return ("void", 0.0)


def settle_bets(conn, results_by_team: dict, settings) -> dict:
    """Grade every not-yet-settled bet whose match result is known; persist settlements.

    results_by_team is keyed "<home>|<away>" lowercased (see results_from_history).
    """
    bet_repo, settle_repo = BetRepo(conn), SettlementRepo(conn)
    now = dt.datetime.utcnow().isoformat()
    settled = wins = 0
    pnl = 0.0
    for bet in bet_repo.list():
        if bet.get("status") == "settled" or not bet.get("home"):
            continue
        result = results_by_team.get(f"{str(bet['home']).lower()}|{str(bet['away']).lower()}")
        if result is None:
            continue
        grade, profit = grade_bet(bet, result)
        settle_repo.upsert({"bet_id": bet["bet_id"], "grade": grade, "profit": profit,
                            "settled_at": now})
        bet_repo.set_status(bet["bet_id"], "settled")
        settled += 1
        wins += 1 if grade == "win" else 0
        pnl += profit
    return {"settled": settled, "wins": wins, "pnl": pnl,
            "roi": pnl / settled if settled else 0.0}


def results_from_history(history: pd.DataFrame) -> dict:
    """Build {"<home>|<away>" -> result} from a results CSV (lowercased team keys)."""
    out: dict = {}
    if history.empty or "FTHG" not in history.columns:
        return out
    has_corners = {"HC", "AC"} <= set(history.columns)
    for _, r in history.iterrows():
        if pd.isna(r.get("FTHG")) or pd.isna(r.get("FTAG")):
            continue
        res = {"home_goals": int(r["FTHG"]), "away_goals": int(r["FTAG"])}
        if has_corners and pd.notna(r.get("HC")) and pd.notna(r.get("AC")):
            res["home_corners"] = int(r["HC"])
            res["away_corners"] = int(r["AC"])
        out[f"{str(r['HomeTeam']).lower()}|{str(r['AwayTeam']).lower()}"] = res
    return out
