"""Push alerts for high-edge value bets (Telegram). Opt-in; a no-op without a bot token,
so the pipeline never breaks because alerting isn't configured.
"""
from __future__ import annotations
import logging
import requests

log = logging.getLogger(__name__)


def format_alert(flagged: list[dict], min_ev: float) -> str | None:
    """Build a concise alert for bets at/above min_ev. Returns None if there's nothing to send."""
    picks = [b for b in flagged if b.get("ev", 0.0) >= min_ev]
    if not picks:
        return None
    lines = [f"⚽ {len(picks)} value bet(s) ≥ {min_ev * 100:.0f}% EV:"]
    for b in picks:
        teams = f"{b.get('home', '')} v {b.get('away', '')}".strip(" v")
        line = f" {b['line']}" if b.get("line") is not None else ""
        lines.append(f"• {teams} | {b['market']} {b['selection']}{line} "
                     f"@ {b.get('best_odds', b.get('taken_odds'))} ({b['book']}) "
                     f"| EV {b['ev'] * 100:+.1f}%")
    return "\n".join(lines)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str) -> None:
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, text: str) -> bool:
        try:
            resp = requests.post(self.url, json={"chat_id": self.chat_id, "text": text}, timeout=15)
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001 - never let alerting break the pipeline
            log.warning("Telegram alert failed: %s", exc)
            return False


class NullNotifier:
    def send(self, text: str) -> bool:
        return False


def build_notifier(settings):
    if settings.telegram_bot_token and settings.telegram_chat_id:
        return TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
    return NullNotifier()


def notify_value_bets(flagged: list[dict], settings) -> bool:
    """Send a single alert summarizing the day's high-edge bets. Returns True if sent."""
    msg = format_alert(flagged, settings.alert_min_ev)
    if not msg:
        return False
    return build_notifier(settings).send(msg)
