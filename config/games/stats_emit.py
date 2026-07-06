"""Fire-and-forget event emission to stats.ishimura.lol.

Games log significant completions (each hand, spin, or match) as events
in the shared stats schema. Stats being unavailable never blocks gameplay.
"""

import json
import os
import threading
import urllib.request
from datetime import datetime, timezone

STATS_WEBHOOK_URL    = os.environ.get("STATS_WEBHOOK_URL", "")
STATS_WEBHOOK_SECRET = os.environ.get("STATS_WEBHOOK_SECRET", "")


def _post(payload):
    try:
        req = urllib.request.Request(
            STATS_WEBHOOK_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type":   "application/json",
                "X-Stats-Secret": STATS_WEBHOOK_SECRET,
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass


def emit(user, item_type, item_id, item_name="", metadata=None, duration_secs=None, played_at=None):
    """Fire an event to stats. Non-blocking, best-effort.

    - user:          username string
    - item_type:     "chess" | "blackjack" | "war" | "slots" | "baccarat" | ...
    - item_id:       unique per event (game_id, hand row id, etc)
    - item_name:     short human-readable label
    - metadata:      dict of game-specific fields (result, bet, payout, variant, ...)
    - duration_secs: optional game duration
    - played_at:     optional ISO timestamp string; defaults to now(UTC)
    """
    if not STATS_WEBHOOK_URL or not STATS_WEBHOOK_SECRET or not user:
        return
    payload = {
        "user_id":       user,
        "source":        "games",
        "item_type":     item_type,
        "item_id":       str(item_id),
        "item_name":     item_name or item_type,
        "item_metadata": metadata or {},
        "played_at":     played_at or datetime.now(timezone.utc).isoformat(),
        "duration_secs": duration_secs,
    }
    threading.Thread(target=_post, args=(payload,), daemon=True).start()
