"""Daily value-bet report: console + CSV + HTML. Single selections only."""
from __future__ import annotations
import csv
import os

COLUMNS = ["league", "home", "away", "market", "selection", "line",
           "model_prob", "fair_prob", "edge", "ev", "best_odds", "book", "stake",
           "explanation"]

def render(flagged: list[dict], reports_dir: str, date: str) -> tuple[str, str]:
    os.makedirs(reports_dir, exist_ok=True)
    csv_path = os.path.join(reports_dir, f"value_bets_{date}.csv")
    html_path = os.path.join(reports_dir, f"value_bets_{date}.html")

    if not flagged:
        print(f"No value bets today ({date}). A quiet day is a correct result.")

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for b in flagged:
            w.writerow(b)

    rows = "".join(
        "<tr>" + "".join(f"<td>{b.get(c, '')}</td>" for c in COLUMNS) + "</tr>"
        for b in flagged)
    body = (f"<p>No value bets today ({date}).</p>" if not flagged
            else f"<table border=1><tr>{''.join(f'<th>{c}</th>' for c in COLUMNS)}</tr>{rows}</table>")
    html = f"<html><body><h1>Value Bets {date}</h1>{body}</body></html>"
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    for b in flagged:
        print(f"{b['ev']:+.3f} EV | {b['home']} v {b['away']} | {b['market']} "
              f"{b['selection']} {b.get('line') or ''} @ {b['best_odds']} ({b['book']})")
        if b.get("explanation"):
            print(f"    {b['explanation']}")
    return csv_path, html_path
