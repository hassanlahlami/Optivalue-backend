from config.settings import load_settings
import main

def test_build_sources_dry_run():
    s = load_settings("settings.yaml")
    odds, results = main.build_sources(s, dry_run=True)
    from sources.sample import SampleSource
    assert isinstance(odds, SampleSource)
    assert isinstance(results, SampleSource)

def test_run_daily_command_dry_run(tmp_path, monkeypatch):
    s = load_settings("settings.yaml")
    object.__setattr__(s, "db_path", str(tmp_path / "t.db"))
    object.__setattr__(s, "reports_dir", str(tmp_path / "out"))
    monkeypatch.setattr(main, "load_settings", lambda *a, **k: s)
    rc = main.main(["run-daily", "--dry-run", "--date", "2026-06-25"])
    assert rc == 0
