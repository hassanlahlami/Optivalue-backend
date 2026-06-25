"""On-disk JSON cache + polite rate limiting + retry with exponential backoff."""
from __future__ import annotations
import hashlib
import json
import logging
import os
import time
import requests

log = logging.getLogger(__name__)
_last_call: dict[str, float] = {}

def _key(url: str, params: dict) -> str:
    raw = url + "?" + json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()

def cached_get(url: str, params: dict, cache_dir: str, ttl: int,
               min_interval: float = 1.0, max_retries: int = 4):
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, _key(url, params) + ".json")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < ttl:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    host = url.split("/")[2]
    wait = min_interval - (time.time() - _last_call.get(host, 0))
    if wait > 0:
        time.sleep(wait)

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=20)
            _last_call[host] = time.time()
            if resp.status_code == 429:
                raise requests.HTTPError("429 rate limited")
            resp.raise_for_status()
            data = resp.json()
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            return data
        except (requests.RequestException, ValueError) as exc:
            log.warning("GET %s failed (attempt %d/%d): %s", url, attempt, max_retries, exc)
            if attempt == max_retries:
                raise
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("unreachable")
