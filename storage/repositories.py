"""Thin repositories over the SQLite tables. No business logic here."""
from __future__ import annotations
import sqlite3

def _rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]

class MatchRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
    def upsert(self, match: dict) -> None:
        self.conn.execute(
            """INSERT INTO matches(match_id, league, home, away, kickoff_utc, status)
               VALUES(:match_id, :league, :home, :away, :kickoff_utc, :status)
               ON CONFLICT(match_id) DO UPDATE SET
                 league=excluded.league, home=excluded.home, away=excluded.away,
                 kickoff_utc=excluded.kickoff_utc, status=excluded.status""", match)
        self.conn.commit()
    def get(self, match_id: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM matches WHERE match_id=?", (match_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    def set_weather(self, match_id: str, weather: str) -> None:
        self.conn.execute("UPDATE matches SET weather=? WHERE match_id=?", (weather, match_id))
        self.conn.commit()

class OddsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
    def insert_snapshot(self, row: dict) -> None:
        self.conn.execute(
            """INSERT INTO odds_snapshots(match_id, market, selection, line, book,
                 decimal_odds, captured_at, snapshot_type)
               VALUES(:match_id, :market, :selection, :line, :book,
                 :decimal_odds, :captured_at, :snapshot_type)""", row)
        self.conn.commit()
    def closing_for(self, match_id, market, selection, line) -> float | None:
        cur = self.conn.execute(
            """SELECT decimal_odds FROM odds_snapshots
               WHERE match_id=? AND market=? AND selection=? AND snapshot_type='closing'
                 AND (line IS ? OR line=?)
               ORDER BY captured_at DESC LIMIT 1""",
            (match_id, market, selection, line, line))
        row = cur.fetchone()
        return row["decimal_odds"] if row else None

class BetRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
    def insert(self, bet: dict) -> int:
        row = {"explanation": None, **bet}  # explanation optional for older callers
        cur = self.conn.execute(
            """INSERT INTO bets(timestamp, match_id, league, market, selection, line,
                 model_prob, fair_prob, edge, ev, taken_odds, book, stake, status, explanation)
               VALUES(:timestamp, :match_id, :league, :market, :selection, :line,
                 :model_prob, :fair_prob, :edge, :ev, :taken_odds, :book, :stake, :status,
                 :explanation)""",
            row)
        self.conn.commit()
        return int(cur.lastrowid)
    def list(self, status: str | None = None, date: str | None = None,
             match_id: str | None = None) -> list[dict]:
        # Join match info so API consumers get team names; expose taken_odds as best_odds
        # (the best line-shopped price we recorded for the selection).
        q = ("SELECT b.*, b.taken_odds AS best_odds, "
             "m.home AS home, m.away AS away, m.kickoff_utc AS kickoff_utc, "
             "m.league AS match_league, m.weather AS weather "
             "FROM bets b LEFT JOIN matches m ON b.match_id = m.match_id")
        clauses, params = [], []
        if status:
            clauses.append("b.status=?"); params.append(status)
        if date:
            clauses.append("substr(b.timestamp,1,10)=?"); params.append(date)
        if match_id:
            clauses.append("b.match_id=?"); params.append(match_id)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY b.ev DESC"
        return _rows(self.conn.execute(q, params))

    def for_match(self, match_id: str) -> list[dict]:
        return self.list(match_id=match_id)
    def open_bets(self) -> list[dict]:
        return self.list(status="open")
    def set_status(self, bet_id: int, status: str) -> None:
        self.conn.execute("UPDATE bets SET status=? WHERE bet_id=?", (status, bet_id))
        self.conn.commit()
    def set_placed(self, bet_id: int, placed: bool) -> None:
        self.conn.execute("UPDATE bets SET placed=? WHERE bet_id=?", (1 if placed else 0, bet_id))
        self.conn.commit()

class ClvRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
    def upsert(self, row: dict) -> None:
        self.conn.execute(
            """INSERT INTO clv(bet_id, closing_odds, closing_fair_prob, clv_price,
                 clv_prob, settled_at)
               VALUES(:bet_id, :closing_odds, :closing_fair_prob, :clv_price,
                 :clv_prob, :settled_at)
               ON CONFLICT(bet_id) DO UPDATE SET
                 closing_odds=excluded.closing_odds,
                 closing_fair_prob=excluded.closing_fair_prob,
                 clv_price=excluded.clv_price, clv_prob=excluded.clv_prob,
                 settled_at=excluded.settled_at""", row)
        self.conn.commit()
    def all(self) -> list[dict]:
        return _rows(self.conn.execute("SELECT * FROM clv"))

class SettlementRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
    def upsert(self, row: dict) -> None:
        self.conn.execute(
            """INSERT INTO settlements(bet_id, grade, profit, settled_at)
               VALUES(:bet_id, :grade, :profit, :settled_at)
               ON CONFLICT(bet_id) DO UPDATE SET
                 grade=excluded.grade, profit=excluded.profit, settled_at=excluded.settled_at""",
            row)
        self.conn.commit()
    def all(self) -> list[dict]:
        return _rows(self.conn.execute("SELECT * FROM settlements"))
