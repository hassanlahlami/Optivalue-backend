"""CLV report: console + CSV + HTML. CLV is primary; P/L is secondary."""
from __future__ import annotations
import csv
import os

def render(summary: dict, reports_dir: str) -> tuple[str, str]:
    os.makedirs(reports_dir, exist_ok=True)
    csv_path = os.path.join(reports_dir, "clv_report.csv")
    html_path = os.path.join(reports_dir, "clv_report.html")

    verdict = ("reliable" if summary["reliable"]
               else f"not yet reliable (have {summary['sample_size']} settled bets)")

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value"])
        for k in ("sample_size", "pct_positive_clv", "mean_clv_price",
                  "mean_clv_prob", "reliable"):
            w.writerow([k, summary[k]])

    banner = ("" if summary["reliable"]
              else "<p style='color:#b00'><b>Verdict: not yet reliable</b> — "
                   "too few settled bets. Keep logging.</p>")
    html = (f"<html><body><h1>CLV Report</h1>{banner}"
            f"<p>Sample size: {summary['sample_size']} ({verdict})</p>"
            f"<p>% positive CLV: {summary['pct_positive_clv']:.1f}%</p>"
            f"<p>Mean CLV (price): {summary['mean_clv_price']:+.4f}</p>"
            f"<p>Mean CLV (prob): {summary['mean_clv_prob']:+.4f}</p>"
            f"<p><i>Profit/loss is secondary to CLV.</i></p></body></html>")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"CLV: {summary['pct_positive_clv']:.1f}% positive | mean {summary['mean_clv_price']:+.4f} "
          f"| n={summary['sample_size']} | {verdict}")
    return csv_path, html_path
