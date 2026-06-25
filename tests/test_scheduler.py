from scheduler import build_jobs


class _Settings:
    schedule_daily_hour = 9
    schedule_closing_hour = 18


def test_build_jobs_has_cycle_and_closing():
    jobs = build_jobs(_Settings())
    actions = {j["action"] for j in jobs}
    assert actions == {"cycle", "fetch-closing"}


def test_build_jobs_uses_configured_hours():
    jobs = {j["action"]: j for j in build_jobs(_Settings())}
    assert jobs["cycle"]["hour"] == 9
    assert jobs["fetch-closing"]["hour"] == 18
