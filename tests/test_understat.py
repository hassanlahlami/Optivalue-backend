from sources.xg_understat import parse_understat

# Minimal Understat-shaped page: one finished match (with xG) + one unplayed (to be skipped).
SAMPLE = (
    "<script>var datesData = JSON.parse('["
    '{"isResult":true,"datetime":"2024-08-10 17:30:00",'
    '"h":{"id":"1","title":"Manchester City","short_title":"MCI"},'
    '"a":{"id":"2","title":"Chelsea","short_title":"CHE"},'
    '"goals":{"h":"2","a":"1"},"xG":{"h":"2.3","a":"0.9"}},'
    '{"isResult":false,"datetime":"2025-01-01 15:00:00",'
    '"h":{"title":"Arsenal"},"a":{"title":"Spurs"},'
    '"goals":{"h":null,"a":null},"xG":{"h":null,"a":null}}'
    "]')</script>"
)


def test_parse_extracts_finished_match_with_xg_and_alias():
    df = parse_understat(SAMPLE)
    assert len(df) == 1                       # the unplayed match is skipped
    row = df.iloc[0]
    assert row["HomeTeam"] == "Man City"      # alias applied for odds-name consistency
    assert row["AwayTeam"] == "Chelsea"
    assert row["FTHG"] == 2 and row["FTAG"] == 1
    assert row["HxG"] == 2.3 and row["AxG"] == 0.9


def test_parse_returns_empty_without_data_blob():
    assert parse_understat("<html>no datesData here</html>").empty
