#!/usr/bin/env python3
"""Periodically poll slskd's API and re-queue any download that finished in
the 'Completed, Rejected' state. Soulseek peers that only allow one upload at
a time reject queued items rather than waiting; slskd doesn't retry those by
default, so a 50-track album drips through one file at a time and needs
manual restart of each rejected file. This daemon fixes that."""

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("slskd-retry")

SLSKD_BASE  = os.environ.get("SLSKD_URL",       "http://127.0.0.1:5030")
SLSKD_TOKEN = os.environ.get("SLSKD_API_KEY",   "")
INTERVAL    = int(os.environ.get("RETRY_INTERVAL_SECS", "60"))
# Cap how many times we'll retry the same file before giving up (to avoid
# pinging dead peers forever).
MAX_RETRIES = int(os.environ.get("RETRY_MAX_ATTEMPTS", "20"))

_attempts = defaultdict(int)   # (username, filename) -> count


def _api(method, path, body=None):
    url  = f"{SLSKD_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if SLSKD_TOKEN:
        headers["X-API-Key"] = SLSKD_TOKEN
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def find_rejected():
    """Group rejected downloads by user so we can re-queue them as a batch."""
    try:
        downloads = _api("GET", "/api/v0/transfers/downloads") or []
    except Exception as e:
        log.warning("slskd unreachable: %s", e)
        return {}
    by_user = defaultdict(list)
    for user_block in downloads:
        username = user_block.get("username")
        if not username:
            continue
        for d in user_block.get("directories", []) or []:
            for f in d.get("files", []) or []:
                state = f.get("state", "") or ""
                # slskd state strings are comma-separated, e.g.
                # "Completed, Rejected" or "Completed, TimedOut"
                if "Completed" in state and ("Rejected" in state or "TimedOut" in state):
                    key = (username, f.get("filename"))
                    if _attempts[key] >= MAX_RETRIES:
                        continue
                    by_user[username].append({
                        "filename": f.get("filename"),
                        "size":     f.get("size"),
                    })
    return by_user


def requeue(username, files):
    """Re-submit a batch of downloads to a single peer."""
    if not files:
        return 0
    encoded_user = urllib.parse.quote(username, safe="")
    try:
        _api("POST", f"/api/v0/transfers/downloads/{encoded_user}", files)
        for f in files:
            _attempts[(username, f["filename"])] += 1
        return len(files)
    except Exception as e:
        log.warning("requeue failed for %s: %s", username, e)
        return 0


def tick():
    rejected = find_rejected()
    if not rejected:
        return
    total = 0
    for user, files in rejected.items():
        total += requeue(user, files)
    if total:
        log.info("re-queued %d rejected files across %d user(s)",
                 total, len(rejected))


def main():
    log.info("slskd-retry watching %s every %ds (max %d attempts/file)",
             SLSKD_BASE, INTERVAL, MAX_RETRIES)
    while True:
        try:
            tick()
        except Exception:
            log.exception("tick error")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
