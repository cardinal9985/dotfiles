"""KF2 WebAdmin backend.

Talks to the UE3 WebAdmin panel by scraping its HTML forms. The panel is a
built-in server admin on port 8380 (see kf2.nix). Auth is a session cookie
established by POSTing to the login form with the admin password.

Config schema:
    url             base URL of WebAdmin, e.g. http://localhost:8380
    username        WebAdmin login, defaults to "admin"
    password_file   path to a file whose contents are the admin password
                    (comes from sops via kf2/admin_password)
"""

import threading

import requests
from bs4 import BeautifulSoup


class KF2WebAdminBackend:

    capabilities = frozenset({
        "console", "players", "kick", "ban", "player_count",
        "cheatsheet", "change_game",
    })

    # Static KF2 admin command reference. WebAdmin console accepts these
    # via `SendText` on /ServerAdmin/current/console.
    CHEATSHEET = [
        {"category": "Chat", "commands": [
            {"cmd": "Say",           "args": "<message>", "desc": "Chat as admin"},
            {"cmd": "AdminSay",      "args": "<message>", "desc": "Server-wide banner message"},
            {"cmd": "AdminSayNext",  "args": "<message>", "desc": "Message shown on next map load"},
        ]},
        {"category": "Server", "commands": [
            {"cmd": "RestartMap",       "args": "",                  "desc": "Restart the current map"},
            {"cmd": "SwitchLevel",      "args": "<KF-MapName>",      "desc": "Change to another map"},
            {"cmd": "SetGamePassword",  "args": "<password>",        "desc": "Set (or clear with \"\") the server password"},
        ]},
        {"category": "Game", "commands": [
            {"cmd": "SetGameLength",     "args": "0|1|2",           "desc": "Short / Medium / Long"},
            {"cmd": "SetGameDifficulty", "args": "0|1|2|3",         "desc": "Normal / Hard / Suicidal / Hell on Earth"},
            {"cmd": "SetGameType",       "args": "<class>",          "desc": "e.g. KFGameContent.KFGameInfo_Survival"},
            {"cmd": "AdminForceNextMap", "args": "",                  "desc": "Skip to the next voted/scheduled map"},
        ]},
        {"category": "Player", "commands": [
            {"cmd": "Kick",         "args": "<name-or-id>", "desc": "Kick a player (use Players tab for buttons)"},
            {"cmd": "KickBan",      "args": "<name-or-id>", "desc": "Kick + ban a player"},
        ]},
        {"category": "Debug", "commands": [
            {"cmd": "WriteToLog",   "args": "<message>",     "desc": "Write a marker line to the server log"},
            {"cmd": "GetAll",       "args": "<class> <prop>","desc": "Dump a property across all instances (verbose)"},
        ]},
    ]

    # Vanilla KF2 length + difficulty options. Games' difficulty numbering is
    # 0-3 and length is 0-2 across all versions.
    DIFFICULTIES = [
        {"value": "0", "label": "Normal"},
        {"value": "1", "label": "Hard"},
        {"value": "2", "label": "Suicidal"},
        {"value": "3", "label": "Hell on Earth"},
    ]
    LENGTHS = [
        {"value": "0", "label": "Short (4 waves)"},
        {"value": "1", "label": "Medium (7 waves)"},
        {"value": "2", "label": "Long (10 waves)"},
    ]

    def __init__(self, config):
        self.config   = config or {}
        self.base_url = self.config.get("url", "http://localhost:8380").rstrip("/")
        self.username = self.config.get("username", "admin")
        self._pw_file = self.config.get("password_file")
        self.session  = requests.Session()
        self._lock    = threading.Lock()
        self._logged_in = False

    def has(self, cap):
        return cap in self.capabilities

    # -- auth --------------------------------------------------------------

    def _password(self):
        if not self._pw_file:
            return ""
        try:
            with open(self._pw_file, "r") as fh:
                return fh.read().strip()
        except OSError:
            return ""

    def _extract_token(self, html):
        """Login form has a hidden CSRF token. Grab it if present."""
        soup = BeautifulSoup(html, "html.parser")
        el = soup.find("input", attrs={"name": "token"})
        return el.get("value", "") if el else ""

    def _login(self):
        """Establish a fresh session cookie. Returns True on success."""
        try:
            r = self.session.get(f"{self.base_url}/ServerAdmin/", timeout=8)
            if r.status_code != 200:
                return False
            token = self._extract_token(r.text)
            r = self.session.post(
                f"{self.base_url}/ServerAdmin/",
                data={
                    "token":         token,
                    "password_hash": "",
                    "username":      self.username,
                    "password":      self._password(),
                    "remember":      "-1",
                },
                allow_redirects=True,
                timeout=8,
            )
            # Successful login lands on a page that no longer contains the
            # username field. A retained login form means the credentials
            # were rejected.
            self._logged_in = ("name=\"username\"" not in r.text)
            return self._logged_in
        except requests.RequestException:
            self._logged_in = False
            return False

    def _get(self, path):
        """GET behind auth; re-login on 401/redirect back to login page."""
        with self._lock:
            if not self._logged_in and not self._login():
                return None
            try:
                r = self.session.get(f"{self.base_url}{path}", timeout=8,
                                     allow_redirects=True)
            except requests.RequestException:
                return None
            if r.status_code == 200 and "name=\"username\"" not in r.text:
                return r
            # Session expired - try one re-login and one retry.
            if self._login():
                try:
                    r = self.session.get(f"{self.base_url}{path}", timeout=8)
                    return r if r.status_code == 200 else None
                except requests.RequestException:
                    return None
            return None

    def _post(self, path, data):
        with self._lock:
            if not self._logged_in and not self._login():
                return None
            try:
                r = self.session.post(f"{self.base_url}{path}", data=data,
                                      timeout=8, allow_redirects=True)
            except requests.RequestException:
                return None
            if r.status_code == 200 and "name=\"username\"" not in r.text:
                return r
            if self._login():
                try:
                    r = self.session.post(f"{self.base_url}{path}", data=data,
                                          timeout=8)
                    return r if r.status_code == 200 else None
                except requests.RequestException:
                    return None
            return None

    # -- players -----------------------------------------------------------

    def _parse_players(self, html):
        """WebAdmin players table has columns: Name, Ping, Score, Admin, Actions.
        Rows have hidden inputs carrying the player id for the action forms.
        """
        soup = BeautifulSoup(html, "html.parser")
        players = []
        table = soup.find("table", class_="players")
        if not table:
            # Fallback: any table under the current+players page
            table = soup.find("table")
        if not table:
            return players
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            name  = cells[0].get_text(strip=True)
            if not name:
                continue
            ping  = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            score = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            # Try to find a player id in any input inside the row
            pid = ""
            for inp in row.find_all("input"):
                nm = (inp.get("name") or "").lower()
                if nm in ("playerid", "playerkey", "playername"):
                    pid = inp.get("value", "")
                    break
            players.append({
                "id":    pid or name,
                "name":  name,
                "ping":  ping,
                "score": score,
            })
        return players

    def player_list(self):
        r = self._get("/ServerAdmin/current/players")
        if not r:
            return None
        return self._parse_players(r.text)

    def player_count(self):
        pl = self.player_list()
        return len(pl) if pl is not None else None

    # -- console -----------------------------------------------------------

    def send_command(self, command):
        """Fire and forget - output shows up in the journalctl SSE stream."""
        r = self._post("/ServerAdmin/current/console",
                       {"SendText": command, "command": command})
        return "sent" if r is not None else None

    # -- moderation --------------------------------------------------------

    def kick(self, player_id, reason=""):
        r = self._post("/ServerAdmin/current/players/action",
                       {"action": "kick", "playerkey": player_id})
        return r is not None

    def ban(self, player_id, reason=""):
        r = self._post("/ServerAdmin/current/players/action",
                       {"action": "sessionban", "playerkey": player_id})
        return r is not None

    # -- cheatsheet --------------------------------------------------------

    def commands(self):
        return self.CHEATSHEET

    # -- change map / mode / difficulty ------------------------------------

    def _parse_options(self, select_el):
        """Turn a <select> into a list of {value, label} dicts, tracking selected."""
        out = []
        selected = None
        if not select_el:
            return out, selected
        for opt in select_el.find_all("option"):
            val = opt.get("value", "")
            if not val:
                continue
            label = opt.get_text(strip=True) or val
            out.append({"value": val, "label": label})
            if opt.get("selected") is not None:
                selected = val
        return out, selected

    def get_change_options(self):
        r = self._get("/ServerAdmin/current/change")
        if not r:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        maps, cur_map    = self._parse_options(soup.find("select", attrs={"name": "map"}))
        gts,  cur_gt     = self._parse_options(soup.find("select", attrs={"name": "gametype"}))
        return {
            "current": {
                "map":        cur_map or "",
                "gametype":   cur_gt or "",
                "difficulty": "",
                "length":     "",
            },
            "maps":         maps,
            "gametypes":    gts,
            "difficulties": self.DIFFICULTIES,
            "lengths":      self.LENGTHS,
        }

    def change_game(self, map_name=None, gametype=None, difficulty=None,
                    length=None, restart=False, **_):
        """POST /ServerAdmin/current/change with a change or restart action.

        Difficulty + length are pushed via urlextra query args since KF2's
        change form only exposes map + gametype natively.
        """
        extras = []
        if difficulty not in (None, ""):
            extras.append(f"Difficulty={difficulty}")
        if length not in (None, ""):
            extras.append(f"GameLength={length}")
        urlextra = "?" + "?".join(extras) if extras else ""
        data = {
            "action":            "restart" if restart else "change",
            "mutatorGroupCount": "0",
            "urlextra":          urlextra,
        }
        if map_name: data["map"]      = map_name
        if gametype: data["gametype"] = gametype
        r = self._post("/ServerAdmin/current/change", data)
        return r is not None
