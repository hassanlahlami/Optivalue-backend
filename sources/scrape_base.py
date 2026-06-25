"""Polite, ToS-respecting scraping helpers for sources that have no free API.

Principles (matches the project's data-source rules): only fetch what a site's robots.txt
permits, identify ourselves honestly, throttle + back off, and cache aggressively. This module
deliberately does NOT defeat anti-bot protections (no proxy rotation, no CAPTCHA bypass) — those
are both ToS violations and fragile. If a site disallows a path in robots.txt, we skip it.
"""
from __future__ import annotations
import hashlib
import logging
import os
import time
import urllib.robotparser
from urllib.parse import urlsplit
import requests

log = logging.getLogger(__name__)
USER_AGENT = "value-bets-personal/1.0 (personal research bot; respects robots.txt)"
_last_call: dict[str, float] = {}


def robots_allows(url: str, user_agent: str = USER_AGENT) -> bool:
    """Check the site's robots.txt. Missing/unreadable robots.txt is treated as allow-all
    (the standard convention), but an explicit Disallow is honoured."""
    parts = urlsplit(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        rp.read()
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read robots.txt for %s (%s); proceeding", parts.netloc, exc)
        return True
    return rp.can_fetch(user_agent, url)


def polite_get(url: str, cache_dir: str, ttl: int,
               min_interval: float = 2.0, respect_robots: bool = True) -> str:
    """Cached, rate-limited, robots-gated GET returning page text. Raises PermissionError if
    robots.txt disallows the URL."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "scrape_" + hashlib.sha256(url.encode()).hexdigest() + ".html")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < ttl:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    if respect_robots and not robots_allows(url):
        raise PermissionError(f"robots.txt disallows fetching {url} — skipping (by design)")

    host = urlsplit(url).netloc
    wait = min_interval - (time.time() - _last_call.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    _last_call[host] = time.time()
    resp.raise_for_status()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(resp.text)
    return resp.text
