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

    def has(self, cap):
        return cap in self.capabilities


class NullBackend(Backend):
    capabilities = frozenset()
