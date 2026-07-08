import json
import os
import re
import socket
import subprocess
import urllib.request
from pathlib import Path

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_from_directory, stream_with_context, url_for

import backends
from shared_auth import get_user, is_admin

DISCOVERY_DIR = Path(os.environ.get("HANGAR_DISCOVERY_DIR", "/etc/hangar/servers.d"))
PUBLIC_DIR    = Path(os.environ.get("HANGAR_PUBLIC_DIR",    "/etc/hangar/public"))
SYSTEMCTL     = os.environ.get("HANGAR_SYSTEMCTL", "/run/current-system/sw/bin/systemctl")
JOURNALCTL    = os.environ.get("HANGAR_JOURNALCTL", "/run/current-system/sw/bin/journalctl")
ALLOWED_POWER = {"start", "stop", "restart"}
LOG_TAIL_LINES = 200
UNIT_RE       = re.compile(r"^[a-zA-Z0-9@._-]+\.service$")

app = Flask(__name__)


def load_servers():
    """Read every *.json under DISCOVERY_DIR, keyed by slug. Bad files are skipped.

    An entry needs a slug and *either* a valid systemd_unit (for locally-
    managed servers) or a status_probe (for pre-migration games still
    running elsewhere - Pelican containers, external boxes, etc).
    """
    out = {}
    if not DISCOVERY_DIR.is_dir():
        return out
    for path in sorted(DISCOVERY_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        slug = data.get("slug")
        if not slug:
            continue
        unit  = data.get("systemd_unit", "")
        probe = data.get("status_probe")
        if unit and not UNIT_RE.match(unit):
            continue
        if not unit and not probe:
            continue
        out[slug] = data
    return out


# Backend instances cached per-slug so WebAdmin session cookies survive.
_BACKENDS = {}
_BACKENDS_LOCK = None  # created lazily; app is single-process


def get_backend(slug, meta):
    inst = _BACKENDS.get(slug)
    if inst is None:
        inst = backends.make(meta)
        _BACKENDS[slug] = inst
    return inst


def unit_status(unit):
    """Return dict with active state + since + pid. `systemctl is-active` and show don't need sudo."""
    active = subprocess.run(
        [SYSTEMCTL, "is-active", unit],
        capture_output=True, text=True,
    ).stdout.strip() or "unknown"
    show = subprocess.run(
        [SYSTEMCTL, "show", unit,
         "--property=ActiveEnterTimestamp,MainPID,SubState,LoadState"],
        capture_output=True, text=True,
    ).stdout
    props = {}
    for line in show.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k] = v
    return {
        "active":   active,
        "sub":      props.get("SubState", ""),
        "loaded":   props.get("LoadState", ""),
        "since":    props.get("ActiveEnterTimestamp", ""),
        "main_pid": props.get("MainPID", "0"),
    }


def _probe_active(probe):
    """Return "active" if the probe succeeds, else "inactive".

    Supported probe types:
      tcp     - socket connect to (host, port)
      http    - urlopen; treat 2xx/3xx/4xx as active (anything but conn-refused)
      process - pgrep -f <pattern>
    """
    t       = probe.get("type", "tcp")
    host    = probe.get("host", "127.0.0.1")
    port    = probe.get("port")
    timeout = float(probe.get("timeout", 3))
    try:
        if t == "tcp":
            with socket.create_connection((host, int(port)), timeout=timeout):
                return "active"
        if t == "http":
            url = probe.get("url") or f"http://{host}:{port}{probe.get('path', '/')}"
            req = urllib.request.Request(url, method="GET")
            try:
                urllib.request.urlopen(req, timeout=timeout).read(1)
                return "active"
            except urllib.error.HTTPError:
                # Any HTTP response means the service is up (even 401/404).
                return "active"
        if t == "process":
            pat = probe.get("pattern", "")
            if not pat:
                return "inactive"
            proc = subprocess.run(
                ["/run/current-system/sw/bin/pgrep", "-f", pat],
                capture_output=True, timeout=timeout,
            )
            return "active" if proc.returncode == 0 else "inactive"
    except (socket.error, OSError, subprocess.TimeoutExpired, ValueError,
            urllib.error.URLError):
        pass
    return "inactive"


def get_server_status(meta):
    """Return a status dict for either a systemd-managed or probe-based server."""
    unit = meta.get("systemd_unit")
    if unit and UNIT_RE.match(unit):
        return unit_status(unit)
    probe = meta.get("status_probe")
    if probe:
        active = _probe_active(probe)
        return {
            "active":   active,
            "sub":      "probed",
            "loaded":   "external",
            "since":    "",
            "main_pid": "0",
        }
    return {
        "active":   "unknown",
        "sub":      "",
        "loaded":   "",
        "since":    "",
        "main_pid": "0",
    }


def power(unit, action):
    if action not in ALLOWED_POWER:
        raise ValueError(f"disallowed action: {action}")
    if not UNIT_RE.match(unit):
        raise ValueError(f"disallowed unit: {unit}")
    proc = subprocess.run(
        [SYSTEMCTL, action, unit],
        capture_output=True, text=True, timeout=30,
    )
    return proc.returncode, (proc.stderr or proc.stdout).strip()


@app.before_request
def require_admin():
    # Bypass for health and public assets (banner served to KF2 clients).
    if request.path == "/healthz" or request.path.startswith("/public/"):
        return None
    user = get_user()
    if not user:
        return "Unauthorized", 401
    if not is_admin() and not app.debug:
        return "Forbidden - admin group required", 403


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/public/<path:filename>")
def public_asset(filename):
    # Safe against traversal - send_from_directory rejects anything that
    # escapes the base dir.
    return send_from_directory(str(PUBLIC_DIR), filename)


@app.route("/public/status")
def public_status():
    """Lightweight per-server status feed consumed by normandy's homepage
    poller. No auth - the same up/down info is already shown on the public
    homepage. Uses `homepage_slug` from discovery when set so the JSON keys
    match the homepage's tile slugs directly.
    """
    servers = load_servers()
    out = []
    for slug, meta in servers.items():
        status = get_server_status(meta)
        pc = None
        backend = get_backend(slug, meta)
        if status["active"] == "active" and backend.has("player_count"):
            pc = backend.player_count()
        out.append({
            "slug":         meta.get("homepage_slug") or slug,
            "hangar_slug":  slug,
            "active":       status["active"],
            "player_count": pc,
        })
    return jsonify(out)


@app.route("/")
def index():
    servers = load_servers()
    rows = []
    for slug, meta in servers.items():
        status = get_server_status(meta)
        backend = get_backend(slug, meta)
        pc = None
        if status["active"] == "active" and backend.has("player_count"):
            pc = backend.player_count()
        rows.append({
            "slug":         slug,
            "name":         meta.get("name", slug),
            "game":         meta.get("game_type", ""),
            "connect":      meta.get("connect_address", ""),
            "status":       status,
            "player_count": pc,
        })
    return render_template("list.html", user=get_user(), servers=rows)


@app.route("/server/<slug>")
def server_detail(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    status = get_server_status(meta)
    backend = get_backend(slug, meta)
    caps = sorted(backend.capabilities)
    return render_template("server.html", user=get_user(), s=meta, status=status,
                           caps=caps)


@app.route("/server/<slug>/players")
def server_players(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("players"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    players = backend.player_list()
    return jsonify({"ok": players is not None, "players": players or []})


@app.route("/server/<slug>/console", methods=["POST"])
def server_console(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("console"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    payload = request.get_json(silent=True) or {}
    command = (request.form.get("command") or payload.get("command") or "").strip()
    if not command:
        return jsonify({"ok": False, "error": "empty command"}), 400
    if len(command) > 500:
        return jsonify({"ok": False, "error": "command too long"}), 400
    result = backend.send_command(command)
    return jsonify({"ok": result is not None, "result": result or ""})


@app.route("/server/<slug>/players/<path:player_id>/kick", methods=["POST"])
def server_kick(slug, player_id):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("kick"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    ok = backend.kick(player_id)
    return jsonify({"ok": ok})


@app.route("/server/<slug>/players/<path:player_id>/ban", methods=["POST"])
def server_ban(slug, player_id):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("ban"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    ok = backend.ban(player_id)
    return jsonify({"ok": ok})


@app.route("/server/<slug>/cheatsheet")
def server_cheatsheet(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("cheatsheet"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    return jsonify({"ok": True, "categories": backend.commands() or []})


@app.route("/server/<slug>/change/options")
def server_change_options(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("change_game"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    opts = backend.get_change_options()
    if opts is None:
        return jsonify({"ok": False, "error": "backend unavailable"}), 502
    return jsonify({"ok": True, **opts})


@app.route("/server/<slug>/bans")
def server_bans(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("bans"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    bans = backend.get_bans()
    if bans is None:
        return jsonify({"ok": False, "error": "backend unavailable"}), 502
    return jsonify({"ok": True, **bans})


@app.route("/server/<slug>/bans/add", methods=["POST"])
def server_bans_add(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("bans"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    p = request.get_json(silent=True) or {}
    kind   = (p.get("kind")   or "").strip()
    value  = (p.get("value")  or "").strip()
    reason = (p.get("reason") or "").strip()
    if kind not in ("session", "id", "ip"):
        return jsonify({"ok": False, "error": "invalid kind"}), 400
    if not value:
        return jsonify({"ok": False, "error": "empty value"}), 400
    ok = backend.add_ban(kind, value, reason)
    return jsonify({"ok": ok})


@app.route("/server/<slug>/bans/remove", methods=["POST"])
def server_bans_remove(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("bans"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    p = request.get_json(silent=True) or {}
    kind = (p.get("kind") or "").strip()
    key  = (p.get("key")  or "").strip()
    if kind not in ("session", "id", "ip") or not key:
        return jsonify({"ok": False, "error": "invalid"}), 400
    ok = backend.remove_ban(kind, key)
    return jsonify({"ok": ok})


@app.route("/server/<slug>/password", methods=["POST"])
def server_password(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("passwords"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    p = request.get_json(silent=True) or {}
    kind = (p.get("kind") or "").strip()
    pw   = p.get("password") or ""
    if kind not in ("game", "admin"):
        return jsonify({"ok": False, "error": "invalid kind"}), 400
    ok = backend.set_password(kind, pw)
    return jsonify({"ok": ok})


@app.route("/server/<slug>/welcome")
def server_welcome_get(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("welcome"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    w = backend.get_welcome()
    if w is None:
        return jsonify({"ok": False, "error": "backend unavailable"}), 502
    return jsonify({"ok": True, **w})


@app.route("/server/<slug>/welcome", methods=["POST"])
def server_welcome_set(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("welcome"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    p = request.get_json(silent=True) or {}
    ok = backend.set_welcome(
        banner      = p.get("banner"),
        motto       = p.get("motto"),
        motto_color = p.get("motto_color"),
        motd        = p.get("motd"),
        motd_color  = p.get("motd_color"),
    )
    return jsonify({"ok": ok})


@app.route("/server/<slug>/change", methods=["POST"])
def server_change(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("change_game"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    payload = request.get_json(silent=True) or {}
    ok = backend.change_game(
        map_name   = payload.get("map"),
        gametype   = payload.get("gametype"),
        difficulty = payload.get("difficulty"),
        length     = payload.get("length"),
        restart    = bool(payload.get("restart")),
    )
    return jsonify({"ok": ok})


@app.route("/server/<slug>/change/live", methods=["POST"])
def server_change_live(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    backend = get_backend(slug, meta)
    if not backend.has("change_live"):
        return jsonify({"ok": False, "error": "unsupported"}), 400
    payload = request.get_json(silent=True) or {}
    ok = backend.change_live(
        difficulty = payload.get("difficulty"),
        length     = payload.get("length"),
    )
    return jsonify({"ok": ok})


@app.route("/server/<slug>/power", methods=["POST"])
def server_power(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    payload = request.get_json(silent=True) or {}
    action = (request.form.get("action") or payload.get("action") or "").strip()
    if action not in ALLOWED_POWER:
        return jsonify({"ok": False, "error": "invalid action"}), 400
    rc, msg = power(meta["systemd_unit"], action)
    if request.is_json or request.headers.get("Accept", "").startswith("application/json"):
        return jsonify({"ok": rc == 0, "rc": rc, "message": msg})
    return redirect(url_for("server_detail", slug=slug))


@app.route("/server/<slug>/log")
def server_log(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    unit = meta["systemd_unit"]
    if not UNIT_RE.match(unit):
        abort(400)

    def generate():
        # -o cat = message only, --no-pager, -f = follow, -n = pre-load tail
        proc = subprocess.Popen(
            [JOURNALCTL, "-u", unit, "-f", "-n", str(LOG_TAIL_LINES),
             "-o", "cat", "--no-pager"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        try:
            # SSE tells the browser about retry timing; 3s is snappy.
            yield "retry: 3000\n\n"
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                # Guard against embedded newlines splitting the SSE frame.
                for subline in line.rstrip("\n").splitlines() or [""]:
                    yield f"data: {subline}\n\n"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",   # tell nginx/traefik to not buffer
            "Connection":        "keep-alive",
        },
    )


def _server_summary(slug, meta, status):
    backend = get_backend(slug, meta)
    pc = None
    if status["active"] == "active" and backend.has("player_count"):
        pc = backend.player_count()
    return {
        "slug":         slug,
        "name":         meta.get("name", slug),
        "active":       status["active"],
        "connect":      meta.get("connect_address", ""),
        "player_count": pc,
        "capabilities": sorted(backend.capabilities),
    }


@app.route("/api/servers")
def api_servers():
    servers = load_servers()
    out = []
    for slug, meta in servers.items():
        status = get_server_status(meta)
        out.append(_server_summary(slug, meta, status))
    return jsonify(out)


@app.route("/api/server/<slug>/status")
def api_server_status(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    status = get_server_status(meta)
    summary = _server_summary(slug, meta, status)
    summary["status"] = status
    return jsonify(summary)


if __name__ == "__main__":
    # threaded=True so SSE stream doesn't block other requests.
    app.run(host="0.0.0.0", port=int(os.environ.get("HANGAR_PORT", "5010")),
            threaded=True)
