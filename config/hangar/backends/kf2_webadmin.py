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

import sys
import threading

import requests
from bs4 import BeautifulSoup


class KF2WebAdminBackend:

    capabilities = frozenset({
        "console", "players", "kick", "ban", "player_count",
        "cheatsheet", "change_game",
        "bans", "passwords", "welcome",
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

    def _log(self, msg):
        # Prefix so journalctl -u hangar filtering is easy.
        sys.stderr.write(f"[kf2] {msg}\n")
        sys.stderr.flush()

    # -- auth --------------------------------------------------------------

    def _password(self):
        if not self._pw_file:
            return ""
        try:
            with open(self._pw_file, "r") as fh:
                return fh.read().strip()
        except OSError as e:
            self._log(f"password file read failed: {e}")
            return ""

    def _has_login_form(self, html):
        # KF2 login form has id="loginform" and a username input.
        return 'id="loginform"' in html or 'name="username"' in html

    def _login(self):
        """Establish a session by fetching /ServerAdmin/current and POSTing
        credentials back to whatever URL WebAdmin's login form points at.
        """
        try:
            landing = f"{self.base_url}/ServerAdmin/current"
            r = self.session.get(landing, timeout=8, allow_redirects=True)
            self._log(f"login GET {landing} -> {r.status_code} final={r.url}")
            if r.status_code != 200:
                return False
            # If no login form, we're already authenticated.
            soup = BeautifulSoup(r.text, "html.parser")
            form = soup.find("form", id="loginform")
            if not form:
                self._logged_in = True
                self._log("already logged in")
                return True
            action = form.get("action") or "/ServerAdmin/"
            token_el = form.find("input", attrs={"name": "token"})
            token = token_el.get("value", "") if token_el else ""
            login_url = action if action.startswith("http") else (self.base_url + action)
            self._log(f"login POST {login_url} token='{token}'")
            r = self.session.post(login_url, data={
                "token":         token,
                "password_hash": "",
                "username":      self.username,
                "password":      self._password(),
                "remember":      "-1",
            }, allow_redirects=True, timeout=8)
            has_form = self._has_login_form(r.text)
            self._log(f"login result status={r.status_code} still_has_form={has_form}")
            self._logged_in = not has_form
            return self._logged_in
        except requests.RequestException as e:
            self._log(f"login exception: {e}")
            self._logged_in = False
            return False

    def _get(self, path):
        """GET behind auth; re-login on redirect back to login page."""
        with self._lock:
            if not self._logged_in and not self._login():
                return None
            try:
                r = self.session.get(f"{self.base_url}{path}", timeout=8,
                                     allow_redirects=True)
            except requests.RequestException as e:
                self._log(f"GET {path} exception: {e}")
                return None
            if r.status_code == 200 and not self._has_login_form(r.text):
                return r
            self._log(f"GET {path} needs re-login (status={r.status_code})")
            if self._login():
                try:
                    r = self.session.get(f"{self.base_url}{path}", timeout=8)
                    if r.status_code == 200 and not self._has_login_form(r.text):
                        return r
                    self._log(f"GET {path} still failing after re-login (status={r.status_code})")
                except requests.RequestException as e:
                    self._log(f"GET {path} retry exception: {e}")
            return None

    def _post(self, path, data):
        with self._lock:
            if not self._logged_in and not self._login():
                return None
            try:
                r = self.session.post(f"{self.base_url}{path}", data=data,
                                      timeout=8, allow_redirects=True)
            except requests.RequestException as e:
                self._log(f"POST {path} exception: {e}")
                return None
            if r.status_code == 200 and not self._has_login_form(r.text):
                return r
            self._log(f"POST {path} needs re-login (status={r.status_code})")
            if self._login():
                try:
                    r = self.session.post(f"{self.base_url}{path}", data=data,
                                          timeout=8)
                    if r.status_code == 200 and not self._has_login_form(r.text):
                        return r
                    self._log(f"POST {path} still failing after re-login (status={r.status_code})")
                except requests.RequestException as e:
                    self._log(f"POST {path} retry exception: {e}")
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
        """Fire and forget - output shows up in the journalctl SSE stream.

        KF2 WebAdmin's console page URL varies across versions - try the
        top-level `/console` first, fall back to `/current/console`.
        """
        for path in ("/ServerAdmin/console",
                     "/ServerAdmin/current/console",
                     "/ServerAdmin/current+console"):
            r = self._post(path, {"command": command})
            if r is not None:
                self._log(f"send_command via {path}: ok")
                return "sent"
        self._log(f"send_command all paths failed for cmd={command!r}")
        return None

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

    # -- bans --------------------------------------------------------------
    # KF2 WebAdmin's Access Policy page lays out three tables and their
    # add-forms in this order: session bans (by player name), ID bans, IP
    # masks. The delete link on each row carries a `remove=<key>` query arg
    # or a hidden input on the row's remove form.

    # KF2's Access Policy lives across three separate URLs, one per ban type.
    _BAN_PATHS = {
        "session": "/ServerAdmin/policy/sessionbans",
        "id":      "/ServerAdmin/policy/bans",
        "ip":      "/ServerAdmin/policy/ipbans",
    }
    _BAN_KIND_FIELD = {
        "session": "playerkey",
        "id":      "uniqueid",
        "ip":      "ipmask",
    }

    def _parse_ban_row(self, tr, kind):
        cells = tr.find_all("td")
        if not cells:
            return None
        # Skip placeholder rows: "No bans" / "No entries" / any colspan cell.
        if any(td.get("colspan") for td in cells):
            return None
        text_lower = tr.get_text(strip=True).lower()
        if not text_lower or "no bans" in text_lower or "no entries" in text_lower:
            return None
        # Pull the unban key from any hidden input in this row.
        key = ""
        for inp in tr.find_all("input"):
            val = (inp.get("value") or "").strip()
            nm  = (inp.get("name")  or "").lower()
            if nm in ("playerkey", "uniqueid", "ipmask", "remove") and val:
                key = val
                break
        # Row shape: first cell is the primary identifier, middle cells hold
        # extra detail, last cell is the actions form.
        name = cells[0].get_text(strip=True)
        detail_cells = [c.get_text(strip=True) for c in cells[1:-1]]
        detail = " / ".join(x for x in detail_cells if x)
        if not name and not key:
            return None
        return {"key": key or name, "name": name or key, "detail": detail or ""}

    def _fetch_bans_for(self, kind):
        path = self._BAN_PATHS.get(kind)
        if not path:
            return []
        r = self._get(path)
        if not r:
            self._log(f"bans {kind}: fetch failed at {path}")
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        # Prefer .grid tables (WebAdmin's convention). Fall back to any table.
        tables = soup.find_all("table", class_="grid") or soup.find_all("table")
        entries = []
        for table in tables:
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                entry = self._parse_ban_row(tr, kind)
                if entry:
                    entries.append(entry)
        self._log(f"bans {kind}: {len(entries)} entries at {path}")
        return entries

    def get_bans(self):
        return {
            "session": self._fetch_bans_for("session"),
            "id":      self._fetch_bans_for("id"),
            "ip":      self._fetch_bans_for("ip"),
        }

    def add_ban(self, kind, value, reason=""):
        field = self._BAN_KIND_FIELD.get(kind)
        path  = self._BAN_PATHS.get(kind)
        if not field or not path or not value:
            return False
        data = {"action": "add", field: value}
        if reason:
            data["reason"] = reason
        r = self._post(path, data)
        return r is not None

    def remove_ban(self, kind, key):
        field = self._BAN_KIND_FIELD.get(kind)
        path  = self._BAN_PATHS.get(kind)
        if not field or not path or not key:
            return False
        r = self._post(path, {"action": "delete", field: key})
        return r is not None

    # -- passwords ---------------------------------------------------------
    # KF2's server + admin passwords live on the general settings page.
    # We only ever POST new values; WebAdmin never returns them in cleartext.

    def set_password(self, kind, password):
        if kind not in ("game", "admin"):
            return False
        field = "GamePassword" if kind == "game" else "AdminPassword"
        # WebAdmin uses double-entry confirmation on the settings form.
        r = self._post("/ServerAdmin/settings/general", {
            field:                password,
            f"{field}_confirm":   password,
        })
        return r is not None

    # -- welcome screen (MOTD) --------------------------------------------

    _WELCOME_URL = "/ServerAdmin/settings/welcome"

    def get_welcome(self):
        r = self._get(self._WELCOME_URL)
        if not r:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        banner = ""
        el = soup.find("input", attrs={"name": lambda n: n and "banner" in n.lower()})
        if el:
            banner = el.get("value", "")
        # Boxes: WebAdmin numbers them 0..3 (or 1..4). Look for any input/
        # textarea whose name contains "message" or "line" and group by index.
        boxes = []
        for i in range(4):
            title_el = (
                soup.find("input",    attrs={"name": lambda n, i=i: n and f"messagetitle{i}"  in n.lower()}) or
                soup.find("input",    attrs={"name": lambda n, i=i: n and f"messageline{i}"   in n.lower()})
            )
            body_el = (
                soup.find("textarea", attrs={"name": lambda n, i=i: n and f"messagebody{i}"   in n.lower()}) or
                soup.find("textarea", attrs={"name": lambda n, i=i: n and f"messagetext{i}"   in n.lower()}) or
                soup.find("textarea", attrs={"name": lambda n, i=i: n and str(i) in n.lower() and "message" in n.lower()})
            )
            boxes.append({
                "title": title_el.get("value", "") if title_el else "",
                "body":  body_el.get_text() if body_el else "",
            })
        return {"banner": banner, "boxes": boxes}

    def set_welcome(self, banner, boxes):
        # POST the payload back. Field names mirror what get_welcome inspects.
        data = {"BannerImage": banner or ""}
        for i, box in enumerate((boxes or [])[:4]):
            data[f"MessageTitle{i}"] = box.get("title", "")
            data[f"MessageBody{i}"]  = box.get("body",  "")
        r = self._post(self._WELCOME_URL, data)
        return r is not None
