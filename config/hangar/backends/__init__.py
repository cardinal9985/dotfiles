from .base import Backend, NullBackend
from .kf2_webadmin import KF2WebAdminBackend
from .vs_stdin import VintageStoryStdinBackend

_REGISTRY = {
    "kf2_webadmin": KF2WebAdminBackend,
    "vs_stdin":     VintageStoryStdinBackend,
}


def make(discovery):
    """Return a Backend instance for a discovery dict, or NullBackend if unsupported."""
    kind = discovery.get("console_backend")
    if not kind:
        return NullBackend({})
    cls = _REGISTRY.get(kind)
    if not cls:
        return NullBackend({})
    cfg = discovery.get("console_backend_config", {}) or {}
    return cls(cfg)
