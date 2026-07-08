class Backend:
    """Server-specific admin surface.

    Subclasses set `capabilities` to a set of the strings any of:
        {"console", "players", "kick", "ban", "player_count"}
    and implement only the corresponding methods. Unsupported operations
    return None (readers) or False (writers) so the UI can degrade cleanly.
    """

    capabilities = frozenset()

    def __init__(self, config):
        self.config = config or {}

    def player_count(self):
        return None

    def player_list(self):
        return None

    def send_command(self, command):
        return None

    def kick(self, player_id, reason=""):
        return False

    def ban(self, player_id, reason=""):
        return False

    def commands(self):
        """Optional command cheatsheet.

        Return a list of {"category": str, "commands": [{"cmd", "args", "desc"}]}.
        """
        return None

    def get_change_options(self):
        """Optional current settings + available choices for map/mode change.

        Return dict:
            current: { map, gametype, difficulty, length }
            maps:      [ { value, label } ]
            gametypes: [ { value, label } ]
            difficulties: [ { value, label } ]
            lengths:      [ { value, label } ]
        """
        return None

    def change_game(self, **kwargs):
        return False

    def change_live(self, **kwargs):
        """Live-change difficulty/length without a map reload."""
        return False

    def get_bans(self):
        """Return {"session": [...], "id": [...], "ip": [...]} or None.

        Each entry: {"key": <opaque unban token>, "name": str, "detail": str}
        """
        return None

    def add_ban(self, kind, value, reason=""):
        """kind: "session" | "id" | "ip". Returns bool."""
        return False

    def remove_ban(self, kind, key):
        return False

    def set_password(self, kind, password):
        """kind: "game" | "admin"."""
        return False

    def get_welcome(self):
        """Return {"banner": str, "boxes": [{title, body}, ...]} or None."""
        return None

    def set_welcome(self, banner, boxes):
        return False

    def has(self, cap):
        return cap in self.capabilities


class NullBackend(Backend):
    capabilities = frozenset()
