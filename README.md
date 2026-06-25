# Football Value-Bet Backend

Computes our own model probabilities (Dixon-Coles goals + team-strength corners),
compares them to de-vigged bookmaker odds, and flags positive-EV single bets with
line shopping. Tracks Closing Line Value (CLV) as the real edge test.

## Quick start (no API keys needed)
    pip install -r requirements.txt
    python main.py run-daily --dry-run --date 2026-06-25   # uses bundled samples
    python main.py serve-api                               # http://127.0.0.1:8000/api/docs

## The math
- Implied prob = 1 / decimal_odds. De-vig removes the bookmaker margin so a market's
  fair probabilities sum to 1 (proportional by default; shin/power available).
- edge = model_prob - fair_prob.
- EV = model_prob * best_decimal_odds - 1. We keep selections with EV > threshold.
- Line shopping: across books we record and bet the BEST price for each selection.
- CLV = taken_odds / closing_odds - 1. Consistently positive CLV — not short-run W/L —
  is what proves an edge. The CLV verdict stays "not yet reliable" below ~150 settled bets.

## Live data
1. Copy `.env.example` to `.env`.
2. Get a free key at https://the-odds-api.com (500 requests/month) -> ODDS_API_KEY.
3. (Optional) https://www.football-data.org/client/register -> FOOTBALL_DATA_ORG_KEY.
   Historical fitting uses football-data.co.uk CSVs, which need NO key.
4. `python main.py run-daily` (omit --dry-run).

## Automation (Phase 2)
- `python main.py cycle` — one full daily cycle: run-daily -> alert -> capture closing -> settle -> CLV.
- `python main.py settle` — grade finished bets by result (win/loss/void), realized P/L (secondary to CLV).
- `python main.py bankroll` — bankroll curve + Monte-Carlo risk-of-ruin over open bets.
- `python main.py schedule` — in-process scheduler (needs `pip install apscheduler`): runs `cycle` at
  `schedule_daily_hour` and `fetch-closing` at `schedule_closing_hour` from settings.yaml.
- **Alerts:** set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in `.env` to get a push when bets clear
  `alert_min_ev`. Blank = disabled.

## Edge validation (Phase 1)
- `python main.py backtest` — out-of-sample model report card (Brier, log-loss, calibration vs baseline).
- `python main.py clv-backtest [--folds N]` — tune the model/market blend by CLV; `--folds` = walk-forward.
  Set the winning `blend_weight` in settings.yaml; the live pipeline blends model toward market with it.

## Scheduling (dependency-free alternative)
- Windows Task Scheduler: create a Basic Task running
  `python C:\path\to\backend\main.py cycle` daily.
- cron: `0 9 * * *  cd /path/backend && python main.py cycle`

## Configuration
Edit `settings.yaml` — leagues, markets, books, ev_threshold, devig_method,
goals/corners lines, time-decay xi, Kelly fraction, CLV reliability threshold.

Each league has a `history_source` (`footballdata_couk` for club leagues, `international`
for national teams) and a `model_group`. Leagues in the same `model_group` share one fitted
Dixon-Coles model; club and international teams are kept in separate groups.

### National teams / World Cup 2026
`soccer_fifa_world_cup` is configured with `history_source: international` and
`model_group: international`. Fitting data comes from the free martj42/international_results
dataset (national-team results), so it prices 1X2 and over/under goals. **Corners are
unavailable for internationals** (no free corner data) and are auto-disabled for that group.
Dataset team names are mapped to The Odds API spelling in
`sources/results_international.py` (`TEAM_ALIASES`) — extend it if a team is missing.
Note: international home advantage is approximate (many World Cup games are at neutral venues).
Verify the live sport key with `GET /v4/sports` on The Odds API while the tournament is on.

## Frontend
The UI is a SEPARATE Next.js app under `../frontend` that consumes this API. This
backend never renders HTML beyond the simple report files.
