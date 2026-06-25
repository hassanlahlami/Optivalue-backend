import sources.odds_theoddsapi as oddsmod
from sources.odds_theoddsapi import TheOddsAPIClient

SAMPLE_API = [
  {"id": "x1", "sport_key": "soccer_epl", "commence_time": "2026-06-25T14:00:00Z",
   "home_team": "Arsenal", "away_team": "Chelsea",
   "bookmakers": [{"key": "pinnacle", "markets": [
       {"key": "h2h", "outcomes": [
           {"name": "Arsenal", "price": 2.1},
           {"name": "Chelsea", "price": 3.6},
           {"name": "Draw", "price": 3.4}]}]}]}
]

def test_fetch_odds_normalizes(monkeypatch):
    monkeypatch.setattr(oddsmod, "cached_get", lambda *a, **k: SAMPLE_API)
    client = TheOddsAPIClient("KEY", ".cache", 3600, markets=["h2h", "totals_goals"])
    odds = client.fetch_odds(["soccer_epl"])
    assert any(o.selection == "Arsenal" and o.book == "pinnacle" for o in odds)
