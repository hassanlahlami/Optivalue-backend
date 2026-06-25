"""In-process scheduler for the daily automation (optional; cron / Windows Task Scheduler are
documented in the README as the dependency-free alternative).

build_jobs() is pure and testable; run_scheduler() lazily imports APScheduler so the rest of the
project works whether or not APScheduler is installed.
"""
from __future__ import annotations
import logging

log = logging.getLogger(__name__)


def build_jobs(settings) -> list[dict]:
    """Return the scheduled job specs: a daily full cycle and a closing-odds capture."""
    return [
        {"id": "daily-cycle", "action": "cycle", "hour": settings.schedule_daily_hour, "minute": 0},
        {"id": "closing-capture", "action": "fetch-closing",
         "hour": settings.schedule_closing_hour, "minute": 0},
    ]


def run_scheduler(settings, runner) -> None:
    """Block, running `runner(action)` on the configured cron times.

    runner: callable taking an action name ("cycle" / "fetch-closing"). APScheduler is imported
    here so it's only required when you actually run the scheduler.
    """
    from apscheduler.schedulers.blocking import BlockingScheduler

    sched = BlockingScheduler()
    for job in build_jobs(settings):
        sched.add_job(lambda action=job["action"]: runner(action), "cron",
                      hour=job["hour"], minute=job["minute"], id=job["id"])
        log.info("scheduled %s at %02d:%02d", job["action"], job["hour"], job["minute"])
    print("Scheduler running (Ctrl+C to stop). Jobs: "
          + ", ".join(f"{j['action']}@{j['hour']:02d}:00" for j in build_jobs(settings)))
    sched.start()
