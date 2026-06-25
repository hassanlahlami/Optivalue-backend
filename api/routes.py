"""Mostly read-only JSON routes over SQLite. The one write (mark a bet as placed) is a
deliberate, localhost-only exception for the "track this bet" workflow."""
from __future__ import annotations
import datetime as dt
import json
import os
from fastapi import APIRouter, Body, Depends, Query
from storage.db import connect, migrate
from storage.repositories import BetRepo, MatchRepo
from pipeline.clv import compute_clv

def build_router(settings):
    router = APIRouter(prefix="/api")

    def get_conn():
        conn = connect(settings.db_path)
        migrate(conn)
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/health")
    def health():
        return {"status": "ok"}

    @router.get("/value-bets")
    def value_bets(date: str | None = Query(default=None), conn=Depends(get_conn)):
        date = date or dt.date.today().isoformat()
        rows = BetRepo(conn).list(date=date)
        return sorted(rows, key=lambda r: r["ev"], reverse=True)

    @router.get("/bets")
    def bets(status: str | None = Query(None), conn=Depends(get_conn)):
        return BetRepo(conn).list(status=status)

    @router.get("/matches/{match_id}")
    def match_detail(match_id: str, conn=Depends(get_conn)):
        return {"match": MatchRepo(conn).get(match_id),
                "bets": BetRepo(conn).for_match(match_id)}

    @router.post("/bets/{bet_id}/placed")
    def set_placed(bet_id: int, placed: bool = Body(..., embed=True), conn=Depends(get_conn)):
        """Mark whether you actually placed this bet (the 'track this bet' workflow)."""
        BetRepo(conn).set_placed(bet_id, placed)
        return {"bet_id": bet_id, "placed": placed}

    @router.get("/report-card")
    def report_card():
        """Serve the last backtest's model report card (written by `python main.py backtest`)."""
        path = os.path.join(settings.reports_dir, "model_report_card.json")
        if not os.path.exists(path):
            return {"available": False,
                    "note": "Run `python main.py backtest` to generate the report card."}
        with open(path, "r", encoding="utf-8") as fh:
            return {"available": True, **json.load(fh)}

    @router.get("/clv-report")
    def clv_report(conn=Depends(get_conn)):
        return compute_clv(conn, settings)

    @router.get("/clv-series")
    def clv_series(conn=Depends(get_conn)):
        """Per-bet CLV over time, for the CLV trend chart."""
        return [dict(r) for r in conn.execute(
            "SELECT settled_at, clv_price FROM clv ORDER BY settled_at")]

    @router.get("/bankroll")
    def bankroll(conn=Depends(get_conn)):
        """Bankroll curve from settled bets + Monte-Carlo risk-of-ruin over open bets."""
        from storage.repositories import SettlementRepo
        from pipeline.bankroll import bankroll_curve, monte_carlo_risk
        profits = [s["profit"] for s in SettlementRepo(conn).all()]
        curve = bankroll_curve(profits, settings.starting_bankroll)
        open_bets = BetRepo(conn).list(status="open")
        mc = [{"win_prob": b["model_prob"], "odds": b["taken_odds"], "stake": b["stake"]}
              for b in open_bets]
        risk = monte_carlo_risk(mc, settings.starting_bankroll, sims=2000)
        return {"starting": settings.starting_bankroll, "current": curve[-1],
                "settled_count": len(profits), "curve": curve,
                "open_count": len(mc), **risk}

    return router
