from config.settings import load_settings

def test_load_settings_defaults(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "abc123")
    s = load_settings("settings.yaml")
    assert s.ev_threshold == 0.0
    assert "h2h" in s.markets
    assert s.devig_method == "proportional"
    assert s.odds_api_key == "abc123"
    assert s.max_goals == 10
    assert 2.5 in s.goals_lines
    assert s.leagues[0].history_code == "E0"
