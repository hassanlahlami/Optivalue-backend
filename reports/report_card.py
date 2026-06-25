"""Model report card: prints + saves backtest metrics. Lower Brier/log-loss = better.

The discipline rule: a model change is an improvement only if it lowers out-of-sample Brier and
log-loss (and, once the CLV backtest is wired, raises CLV). The model should also beat the
base-rate baseline — if it doesn't, it has no skill.
"""
from __future__ import annotations
import json
import os


def render(metrics: dict, reports_dir: str) -> str:
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, "model_report_card.html")
    # Persist the metrics as JSON too, so the API can serve the report card without
    # re-running a (heavy) backtest inside a request.
    with open(os.path.join(reports_dir, "model_report_card.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh)

    if metrics.get("sample_size", 0) == 0:
        note = metrics.get("note", "no testable matches")
        print(f"Backtest: {note}.")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"<html><body><h1>Model Report Card</h1><p>{note}</p></body></html>")
        return path

    beats = metrics["brier"] < metrics["baseline_brier"]
    verdict = "beats base-rate baseline" if beats else "NO skill vs base-rate baseline"

    rows = "".join(
        f"<tr><td>{r['bin_lo']:.1f}-{r['bin_hi']:.1f}</td><td>{r['n']}</td>"
        f"<td>{r['mean_pred']:.3f}</td><td>{r['empirical']:.3f}</td></tr>"
        for r in metrics.get("calibration_home", []))

    html = (
        "<html><body><h1>Model Report Card</h1>"
        f"<p>Out-of-sample matches: {metrics['sample_size']} "
        f"(skipped {metrics['skipped']} with unseen teams)</p>"
        f"<p><b>Brier {metrics['brier']:.4f}</b> vs baseline {metrics['baseline_brier']:.4f} "
        f"&rarr; {verdict}</p>"
        f"<p>Log-loss {metrics['log_loss']:.4f} · ECE(home) {metrics['ece_home']:.4f}</p>"
        "<h2>Home-win calibration</h2>"
        "<table border=1><tr><th>Prob bin</th><th>n</th><th>Mean pred</th>"
        f"<th>Empirical</th></tr>{rows}</table>"
        "<p><i>Lower Brier/log-loss is better. Calibration: mean pred should track empirical.</i></p>"
        "</body></html>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"Backtest n={metrics['sample_size']} | Brier {metrics['brier']:.4f} "
          f"(baseline {metrics['baseline_brier']:.4f}, {verdict}) | "
          f"log-loss {metrics['log_loss']:.4f} | ECE(home) {metrics['ece_home']:.4f}")
    return path
