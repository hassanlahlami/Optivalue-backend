"""CLI entrypoint for the value-bet backend.

Commands:
  run-daily [--dry-run] [--date YYYY-MM-DD]  full pipeline -> reports + store
  fit-model [--dry-run]                      (re)fit models from history (smoke)
  fetch-closing [--dry-run] [--date]         record closing odds for the date
  clv-report                                 compute + render CLV
  serve-api                                  launch FastAPI on 127.0.0.1:8000
"""
from __future__ import annotations
import argparse
import datetime as dt
import sys
from config.settings import load_settings
from logging_setup import configure_logging
from storage.db import connect, migrate
from sources.sample import SampleSource
from sources.odds_theoddsapi import TheOddsAPIClient
from sources.results_footballdata_couk import FootballDataCoUkClient
from sources.results_international import InternationalResultsClient
from sources.results_composite import CompositeResultsClient
from pipeline.run import fit_models, run_daily
from pipeline.clv import record_closing, compute_clv
from pipeline.alerts import notify_value_bets
from reports.daily import render as render_daily
from reports.clv import render as render_clv

def build_sources(settings, dry_run: bool):
    if dry_run:
        s = SampleSource("data/samples")
        return s, s
    odds = TheOddsAPIClient(settings.odds_api_key, settings.cache_dir,
                            settings.cache_ttl_seconds, settings.markets)
    # Route history per league.history_source: club leagues -> football-data.co.uk,
    # national teams -> the international results dataset.
    results = CompositeResultsClient(
        {"footballdata_couk": FootballDataCoUkClient(settings.cache_dir),
         "international": InternationalResultsClient(settings.cache_dir)},
        settings.leagues)
    return odds, results

def _today() -> str:
    return dt.date.today().isoformat()

def _load_history(results, settings):
    """Concatenate every league's historical results (for settlement / result lookup)."""
    import pandas as pd
    frames = []
    for lg in settings.leagues:
        try:
            frames.append(results.fetch_history(lg.history_code))
        except Exception as exc:  # noqa: BLE001
            print(f"history fetch failed for {lg.history_code}: {exc}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="value-bets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("run-daily", "fetch-closing"):
        p = sub.add_parser(name)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--date", default=None)
    sub.add_parser("fit-model").add_argument("--dry-run", action="store_true")
    sub.add_parser("clv-report")
    sub.add_parser("serve-api")
    bt = sub.add_parser("backtest")
    bt.add_argument("--dry-run", action="store_true")
    bt.add_argument("--train-frac", type=float, default=0.7)
    cb = sub.add_parser("clv-backtest")
    cb.add_argument("--dry-run", action="store_true")
    cb.add_argument("--train-frac", type=float, default=0.7)
    cb.add_argument("--folds", type=int, default=1)  # >1 = walk-forward
    sub.add_parser("settle").add_argument("--dry-run", action="store_true")
    sub.add_parser("bankroll")
    cy = sub.add_parser("cycle")  # one full daily cycle: run-daily -> fetch-closing -> settle
    cy.add_argument("--dry-run", action="store_true")
    cy.add_argument("--date", default=None)
    sub.add_parser("schedule").add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    settings = load_settings("settings.yaml")
    configure_logging(settings.reports_dir)
    conn = connect(settings.db_path); migrate(conn)

    try:
        if args.cmd == "run-daily":
            odds, results = build_sources(settings, args.dry_run)
            bundle = fit_models(results, settings)
            date = args.date or _today()
            flagged = run_daily(odds, bundle, conn, settings, date)
            render_daily(flagged, settings.reports_dir, date)
            notify_value_bets(flagged, settings)
            return 0
        if args.cmd == "fit-model":
            _, results = build_sources(settings, getattr(args, "dry_run", False))
            fit_models(results, settings)
            print("Models fitted.")
            return 0
        if args.cmd == "fetch-closing":
            odds, _ = build_sources(settings, args.dry_run)
            n = record_closing(odds, conn, settings, args.date or _today())
            print(f"Recorded {n} closing snapshots.")
            return 0
        if args.cmd == "clv-report":
            render_clv(compute_clv(conn, settings), settings.reports_dir)
            return 0
        if args.cmd == "serve-api":
            # The API opens its own per-request connections; release the startup one
            # before handing control to the (blocking) server so it isn't left orphaned.
            conn.close()
            from api.app import serve
            serve(settings)
            return 0
        if args.cmd == "backtest":
            import pandas as pd
            from backtest.run import holdout_backtest
            from reports.report_card import render as render_card
            _, results = build_sources(settings, args.dry_run)
            frames = []
            for lg in settings.leagues:
                if lg.model_group != "club":
                    continue  # backtest the club goals model (has the most history)
                try:
                    frames.append(results.fetch_history(lg.history_code))
                except Exception as exc:  # noqa: BLE001
                    print(f"history fetch failed for {lg.history_code}: {exc}")
            hist = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            render_card(holdout_backtest(hist, settings, args.train_frac), settings.reports_dir)
            return 0
        if args.cmd == "clv-backtest":
            import pandas as pd
            from backtest.clv_backtest import tune_blend_weight
            _, results = build_sources(settings, args.dry_run)
            frames = []
            for lg in settings.leagues:
                if lg.model_group != "club":
                    continue
                try:
                    frames.append(results.fetch_history(lg.history_code))
                except Exception as exc:  # noqa: BLE001
                    print(f"history fetch failed for {lg.history_code}: {exc}")
            hist = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            if args.folds > 1:
                from backtest.clv_backtest import walk_forward_clv
                wf = walk_forward_clv(hist, settings, args.folds, settings.blend_weight)
                if wf.get("n", 0) == 0:
                    print(f"Walk-forward CLV: {wf.get('note', 'no result')}.")
                else:
                    print(f"Walk-forward CLV ({wf['folds']} folds, w={wf['w']}): n={wf['n']} | "
                          f"beat close {wf['pct_beat_close']:.1f}% | "
                          f"mean CLV {wf['mean_clv'] * 100:+.2f}% | ROI {wf['roi'] * 100:+.2f}%")
                return 0
            out = tune_blend_weight(hist, settings, args.train_frac)
            best = out["best"]
            if not best:
                note = next((r.get("note") for r in out["all"] if r.get("note")), "no result")
                print(f"CLV backtest: {note}.")
                return 0
            print(f"CLV backtest - best blend w={best['w']}: n={best['n']} | "
                  f"beat close {best['pct_beat_close']:.1f}% | mean CLV {best['mean_clv'] * 100:+.2f}% "
                  f"| ROI {best['roi'] * 100:+.2f}%")
            for r in out["all"]:
                if r.get("n", 0) > 0:
                    print(f"  w={r['w']}: n={r['n']} | beat {r['pct_beat_close']:.0f}% | "
                          f"meanCLV {r['mean_clv'] * 100:+.2f}% | ROI {r['roi'] * 100:+.2f}%")
            return 0
        if args.cmd == "settle":
            from pipeline.settle import settle_bets, results_from_history
            _, results = build_sources(settings, args.dry_run)
            s = settle_bets(conn, results_from_history(_load_history(results, settings)), settings)
            print(f"Settled {s['settled']} bets | {s['wins']} wins | "
                  f"P/L {s['pnl']:+.2f}u | ROI {s['roi'] * 100:+.1f}% (P/L is secondary to CLV)")
            return 0
        if args.cmd == "bankroll":
            from storage.repositories import SettlementRepo, BetRepo
            from pipeline.bankroll import bankroll_curve, monte_carlo_risk
            profits = [s["profit"] for s in SettlementRepo(conn).all()]
            curve = bankroll_curve(profits, settings.starting_bankroll)
            open_bets = BetRepo(conn).list(status="open")
            mc = [{"win_prob": b["model_prob"], "odds": b["taken_odds"], "stake": b["stake"]}
                  for b in open_bets]
            risk = monte_carlo_risk(mc, settings.starting_bankroll)
            print(f"Bankroll {curve[-1]:.2f}u (start {settings.starting_bankroll:.0f}, "
                  f"{len(profits)} settled) | risk-of-ruin {risk['risk_of_ruin'] * 100:.1f}% over "
                  f"{len(mc)} open bets | median final {risk['median_final']:.1f}, "
                  f"p05 {risk['p05_final']:.1f}")
            return 0
        if args.cmd == "cycle":
            from pipeline.settle import settle_bets, results_from_history
            date = args.date or _today()
            odds, results = build_sources(settings, args.dry_run)
            bundle = fit_models(results, settings)
            flagged = run_daily(odds, bundle, conn, settings, date)
            render_daily(flagged, settings.reports_dir, date)
            notify_value_bets(flagged, settings)
            record_closing(odds, conn, settings, date)
            s = settle_bets(conn, results_from_history(_load_history(results, settings)), settings)
            render_clv(compute_clv(conn, settings), settings.reports_dir)
            print(f"Cycle complete: {len(flagged)} flagged, {s['settled']} settled.")
            return 0
        if args.cmd == "schedule":
            from scheduler import run_scheduler
            extra = ["--dry-run"] if args.dry_run else []
            run_scheduler(settings, lambda action: main([action, *extra]))
            return 0
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
