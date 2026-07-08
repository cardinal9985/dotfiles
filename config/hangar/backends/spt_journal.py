"""SPT + Fika journal-based player tracker.

SPT emits explicit WebSocket connect/disconnect log lines that include
the player's display name and MongoDB-style profile ID. We tail
`journalctl -u tarkov-spt` in a background thread and maintain a live
map of connected profiles.

Known limitation: SPT drops the notifier WebSocket the moment a client
enters a raid (they switch to raid-mode HTTP polling on /fika/update/*).
So player_count reports "at menu / in hideout" rather than "in raid" -
still a useful "someone is actively using the server" signal.

Config schema:
    systemd_unit  systemd unit name to journalctl-tail
"""

import re
import subprocess
import threading
import time


class SPTJournalBackend:

    capabilities = frozenset({"player_count", "players"})

    # SPT logs are case-inconsistent: connect uses `[WS] Player:` while
    # disconnect uses `[ws] player:`. re.I normalises both.
    _CONNECT = re.compile(
        r"\[WS\]\s+Player:\s+(?P<name>.+?)\s+"
        r"\((?P<pid>[0-9a-f]{24})\)\s+\d+\s+has\s+connected",
        re.I,
    )
    _DISCONNECT = re.compile(
        r"\[WS\]\s+Player:\s+(?P<name>.+?)\s+"
        r"\((?P<pid>[0-9a-f]{24})\)\s+\d+\s+has\s+disconnected",
        re.I,
    )
    _RESET_HINTS = (
        "Server has started",
        "Server: executing startup callbacks",
    )

    def __init__(self, config):
        self.config = config or {}
        self.unit    = self.config.get("systemd_unit", "tarkov-spt.service")
        # Keyed by profile id so a reconnect doesn't inflate the count.
        self._players    = {}
        self._lock       = threading.Lock()
        self._tail_thread = None
        self._start_tail()

    def has(self, cap):
        return cap in self.capabilities

    # -- log tailing ------------------------------------------------------

    def _start_tail(self):
        if self._tail_thread is not None:
            return
        t = threading.Thread(target=self._tail_journal, daemon=True,
                             name="spt-tail")
        t.start()
        self._tail_thread = t

    def _tail_journal(self):
        journalctl = "/run/current-system/sw/bin/journalctl"
        while True:
            try:
                proc = subprocess.Popen(
                    [journalctl, "-u", self.unit, "-f", "-o", "cat",
                     "-n", "0", "--no-pager"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                for line in iter(proc.stdout.readline, ""):
                    self._process_log_line(line)
            except Exception:
                pass
            time.sleep(5)

    def _process_log_line(self, line):
        m = self._CONNECT.search(line)
        if m:
            with self._lock:
                self._players[m.group("pid")] = m.group("name").strip()
            return
        m = self._DISCONNECT.search(line)
        if m:
            with self._lock:
                self._players.pop(m.group("pid"), None)
            return
        if any(hint in line for hint in self._RESET_HINTS):
            with self._lock:
                self._players.clear()

    # -- readers ----------------------------------------------------------

    def player_count(self):
        with self._lock:
            return len(self._players)

    def player_list(self):
        with self._lock:
            return [
                {"id": pid, "name": name, "ping": "", "score": ""}
                for pid, name in sorted(self._players.items(),
                                        key=lambda x: x[1])
            ]
