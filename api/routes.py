"""Read-only JSON routes over SQLite. No business logic duplicated from the pipeline."""
from __future__ import annotations
import datetime as dt
from fastapi import APIRouter, Depends, Query
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

    @router.get("/clv-report")
    def clv_report(conn=Depends(get_conn)):
        return compute_clv(conn, settings)

    return router
