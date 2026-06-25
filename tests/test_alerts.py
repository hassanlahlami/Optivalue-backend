from pipeline.alerts import format_alert, build_notifier, NullNotifier, notify_value_bets

BETS = [
    {"home": "Arsenal", "away": "Chelsea", "market": "h2h", "selection": "Arsenal",
     "line": None, "best_odds": 2.1, "book": "pinnacle", "ev": 0.20},
    {"home": "A", "away": "B", "market": "totals_goals", "selection": "Over",
     "line": 2.5, "best_odds": 2.0, "book": "x", "ev": 0.02},
]


class _NoTokenSettings:
    telegram_bot_token = None
    telegram_chat_id = None
    alert_min_ev = 0.05


def test_format_alert_filters_by_min_ev():
    msg = format_alert(BETS, 0.05)
    assert msg is not None
    assert "Arsenal" in msg
    assert "A v B" not in msg  # the 0.02 EV bet is below threshold


def test_format_alert_none_when_no_picks():
    assert format_alert(BETS, 0.5) is None


def test_build_notifier_is_null_without_token():
    assert isinstance(build_notifier(_NoTokenSettings()), NullNotifier)


def test_notify_without_token_returns_false():
    assert notify_value_bets(BETS, _NoTokenSettings()) is False
