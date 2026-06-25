import pandas as pd
from sources.sample import SampleSource

SAMPLES = "data/samples"

def test_sample_odds_loaded():
    src = SampleSource(SAMPLES)
    odds = src.fetch_odds(["soccer_epl"])
    assert len(odds) > 0
    a = [o for o in odds if o.selection == "Arsenal" and o.market == "h2h"]
    assert {o.book for o in a} == {"pinnacle", "betfair"}

def test_sample_history_loaded():
    src = SampleSource(SAMPLES)
    df = src.fetch_history("E0")
    assert isinstance(df, pd.DataFrame)
    assert {"HomeTeam", "AwayTeam", "FTHG", "FTAG", "HC", "AC"} <= set(df.columns)
    assert len(df) >= 12
