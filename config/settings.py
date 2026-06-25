"""Typed settings loader: reads settings.yaml + .env into a frozen Settings dataclass."""
from __future__ import annotations
from dataclasses import dataclass
import os
import yaml
from dotenv import load_dotenv

@dataclass(frozen=True)
class League:
    key: str
    history_code: str
    # history_source selects which results client supplies fitting data:
    #   "footballdata_couk" (club leagues, has corners) or "international" (national teams).
    history_source: str = "footballdata_couk"
    # model_group buckets leagues that share one fitted model. Club and international
    # teams are disjoint populations, so they get separate Dixon-Coles fits.
    model_group: str = "club"

@dataclass(frozen=True)
class Settings:
    leagues: list[League]
    markets: list[str]
    books: list[str]
    ev_threshold: float
    devig_method: str
    consensus: str
    goals_lines: list[float]
    corners_lines: list[float]
    max_goals: int
    max_corners: int
    time_decay_xi: float
    kelly_fraction: float
    flat_stake: float
    cache_ttl_seconds: int
    clv_reliable_min: int
    db_path: str
    cache_dir: str
    reports_dir: str
    cors_origin: str
    odds_api_key: str | None
    football_data_org_key: str | None
    # LLM explanation generation (optional; falls back to a local template with no key).
    llm_enabled: bool
    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key: str | None
    # Which goals/corners models the live pipeline fits. Compare goals with `compare-models`.
    goals_model: str
    corners_model: str
    # Final prob = blend_weight*model + (1-blend_weight)*de-vigged market. 1.0 = pure model,
    # 0.0 = pure market. Tune with `python main.py clv-backtest` and set the best value here.
    blend_weight: float
    # Isotonic calibration of the final probability (opt-in: validate before trusting it).
    calibrate_enabled: bool
    calibrate_min_samples: int
    starting_bankroll: float
    # Phase 2 — automation: alerting (Telegram) + in-process scheduler.
    alert_min_ev: float
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    schedule_daily_hour: int
    schedule_closing_hour: int

def load_settings(path: str = "settings.yaml") -> Settings:
    load_dotenv()
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    leagues = [League(key=l["key"], history_code=l["history_code"],
                      history_source=l.get("history_source", "footballdata_couk"),
                      model_group=l.get("model_group", "club")) for l in raw["leagues"]]
    return Settings(
        leagues=leagues,
        markets=list(raw["markets"]),
        books=list(raw.get("books", [])),
        ev_threshold=float(raw["ev_threshold"]),
        devig_method=str(raw["devig_method"]),
        consensus=str(raw["consensus"]),
        goals_lines=[float(x) for x in raw["goals_lines"]],
        corners_lines=[float(x) for x in raw["corners_lines"]],
        max_goals=int(raw["max_goals"]),
        max_corners=int(raw["max_corners"]),
        time_decay_xi=float(raw["time_decay_xi"]),
        kelly_fraction=float(raw["kelly_fraction"]),
        flat_stake=float(raw["flat_stake"]),
        cache_ttl_seconds=int(raw["cache_ttl_seconds"]),
        clv_reliable_min=int(raw["clv_reliable_min"]),
        db_path=str(raw["db_path"]),
        cache_dir=str(raw["cache_dir"]),
        reports_dir=str(raw["reports_dir"]),
        cors_origin=str(raw["cors_origin"]),
        odds_api_key=os.getenv("ODDS_API_KEY") or None,
        football_data_org_key=os.getenv("FOOTBALL_DATA_ORG_KEY") or None,
        llm_enabled=bool(raw.get("llm_enabled", True)),
        llm_provider=str(raw.get("llm_provider", "groq")),
        llm_model=str(raw.get("llm_model", "llama-3.1-8b-instant")),
        llm_base_url=str(raw.get("llm_base_url", "https://api.groq.com/openai/v1")),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or None,
        goals_model=str(raw.get("goals_model", "dixon_coles")),
        corners_model=str(raw.get("corners_model", "poisson")),
        blend_weight=float(raw.get("blend_weight", 0.5)),
        calibrate_enabled=bool(raw.get("calibrate_enabled", False)),
        calibrate_min_samples=int(raw.get("calibrate_min_samples", 50)),
        starting_bankroll=float(raw.get("starting_bankroll", 100.0)),
        alert_min_ev=float(raw.get("alert_min_ev", 0.05)),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
        schedule_daily_hour=int(raw.get("schedule_daily_hour", 9)),
        schedule_closing_hour=int(raw.get("schedule_closing_hour", 18)),
    )
