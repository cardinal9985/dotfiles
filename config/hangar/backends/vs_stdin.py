"""Vintage Story backend.

VS 1.x has no first-party HTTP admin API - console commands go through the
server's stdin, and player state is discoverable from server log lines. We
run VS with stdin redirected from a named pipe (see vintagestory.nix); this
backend writes commands to that pipe and maintains a live player set by
tailing journalctl in a background thread.

Config schema:
    fifo          absolute path to the stdin FIFO
    systemd_unit  systemd unit name to journalctl-tail for player events
"""

import os
import re
import subprocess
import threading
import time


class VintageStoryStdinBackend:

    capabilities = frozenset({
        "console", "player_count", "players", "kick", "ban", "cheatsheet",
    })

    # VS admin console commands. Reference:
    # https://wiki.vintagestory.at/index.php/List_of_server_commands
    CHEATSHEET = [
        {"category": "Chat", "commands": [
            {"cmd": "/announce",    "args": "<message>", "desc": "Broadcast a system message"},
            {"cmd": "/say",         "args": "<message>", "desc": "Chat as server"},
        ]},
        {"category": "Players", "commands": [
            {"cmd": "/list",        "args": "",              "desc": "List currently connected players"},
            {"cmd": "/kick",        "args": "<name> [reason]", "desc": "Kick a player"},
            {"cmd": "/ban",         "args": "<name> [reason]", "desc": "Permanent-ban a player"},
            {"cmd": "/op",          "args": "<name>",         "desc": "Grant admin role"},
            {"cmd": "/deop",        "args": "<name>",         "desc": "Revoke admin role"},
            {"cmd": "/whitelist",   "args": "on|off|add|remove <name>", "desc": "Whitelist management"},
        ]},
        {"category": "Server", "commands": [
            {"cmd": "/serverconfig","args": "<key> <value>",  "desc": "e.g. AdvertiseServer on / WhitelistMode off"},
            {"cmd": "/stop",        "args": "",               "desc": "Graceful shutdown (Hangar's STOP button is safer)"},
            {"cmd": "/autosavenow", "args": "",               "desc": "Force an immediate save"},
        ]},
        {"category": "Game", "commands": [
            {"cmd": "/time",        "args": "set <hours>",    "desc": "Set world time (0-24)"},
            {"cmd": "/weather",     "args": "clear|rain|storm", "desc": "Set weather"},
            {"cmd": "/gamemode",    "args": "s|c|a [player]", "desc": "survival / creative / adventure"},
            {"cmd": "/tp",          "args": "<player> [target]", "desc": "Teleport player"},
        ]},
        {"category": "World", "commands": [
            {"cmd": "/worldedit",   "args": "on|off",         "desc": "Toggle worldedit mode"},
            {"cmd": "/we",          "args": "<cmd>",          "desc": "Short alias for worldedit"},
        ]},
    ]

    # Log-line regexes for tracking join/leave. VS's exact wording varies by
    # version; keep alternatives here so we don't have to redeploy to iterate.
    _JOIN_PATTERNS = [
        re.compile(r"Player\s+(\S+)\s+(?:joins|joined|connected)", re.I),
        re.compile(r"(\S+)\s+has\s+joined", re.I),
        re.compile(r"\[Server Event\].*?(\S+)\s+client\S*\s+connect", re.I),
    ]
    _LEAVE_PATTERNS = [
        re.compile(r"Player\s+(\S+)\s+(?:disconnected|left|has left)", re.I),
        re.compile(r"(\S+)\s+has\s+left", re.I),
        re.compile(r"\[Server Event\].*?(\S+)\s+client\S*\s+disconnect", re.I),
    ]
    _RESET_HINTS = ("Server started", "Save game loaded", "Save game reloaded")

    def __init__(self, config):
        self.config    = config or {}
        self.fifo_path = self.config.get("fifo", "/run/vintagestory/stdin")
        self.unit      = self.config.get("systemd_unit", "vintagestory.service")
        self._players  = set()
        self._lock     = threading.Lock()
        self._tail_thread = None
        self._start_tail()

    def has(self, cap):
        return cap in self.capabilities

    # -- log tailing ------------------------------------------------------

    def _start_tail(self):
        if self._tail_thread is not None:
            return
        t = threading.Thread(target=self._tail_journal, daemon=True,
                             name="vs-tail")
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
            # Journalctl died; wait and reconnect (usually a nix rebuild
            # swapping the store paths).
            time.sleep(5)

    def _process_log_line(self, line):
        for pat in self._JOIN_PATTERNS:
            m = pat.search(line)
            if m:
                with self._lock:
                    self._players.add(m.group(1))
                return
        for pat in self._LEAVE_PATTERNS:
            m = pat.search(line)
            if m:
                with self._lock:
                    self._players.discard(m.group(1))
                return
        # Startup / save-reload = drop any stale names from a previous run.
        if any(hint in line for hint in self._RESET_HINTS):
            with self._lock:
                self._players.clear()

    # -- stdin FIFO -------------------------------------------------------

    def send_command(self, command):
        if not command:
            return None
        # VS commands typically start with `/`; forgive callers that forget.
        cmd = command if command.startswith("/") else "/" + command
        try:
            # O_NONBLOCK so we fail fast (ENXIO) when the server is stopped
            # instead of hanging until a reader opens the pipe.
            fd = os.open(self.fifo_path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            return None
        try:
            os.write(fd, (cmd + "\n").encode("utf-8"))
            return "sent"
        except OSError:
            return None
        finally:
            os.close(fd)

    # -- readers ----------------------------------------------------------

    def player_count(self):
        with self._lock:
            return len(self._players)

    def player_list(self):
        with self._lock:
            return [{"id": n, "name": n, "ping": "", "score": ""}
                    for n in sorted(self._players)]

    # -- moderation -------------------------------------------------------

    def kick(self, player_id, reason=""):
        return self.send_command(f"/kick {player_id}") is not None

    def ban(self, player_id, reason=""):
        return self.send_command(f"/ban {player_id}") is not None

    # -- cheatsheet -------------------------------------------------------

    def commands(self):
        return self.CHEATSHEET
