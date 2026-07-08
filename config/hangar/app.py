import json
import os
import re
import subprocess
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from shared_auth import get_user, is_admin

DISCOVERY_DIR = Path(os.environ.get("HANGAR_DISCOVERY_DIR", "/etc/hangar/servers.d"))
SYSTEMCTL     = os.environ.get("HANGAR_SYSTEMCTL", "/run/current-system/sw/bin/systemctl")
SUDO          = os.environ.get("HANGAR_SUDO",      "/run/wrappers/bin/sudo")
ALLOWED_POWER = {"start", "stop", "restart"}
UNIT_RE       = re.compile(r"^[a-zA-Z0-9@._-]+\.service$")

app = Flask(__name__)


def load_servers():
    """Read every *.json under DISCOVERY_DIR, keyed by slug. Bad files are skipped."""
    out = {}
    if not DISCOVERY_DIR.is_dir():
        return out
    for path in sorted(DISCOVERY_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        slug = data.get("slug")
        unit = data.get("systemd_unit", "")
        if not slug or not UNIT_RE.match(unit):
            continue
        out[slug] = data
    return out


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


def power(unit, action):
    if action not in ALLOWED_POWER:
        raise ValueError(f"disallowed action: {action}")
    if not UNIT_RE.match(unit):
        raise ValueError(f"disallowed unit: {unit}")
    proc = subprocess.run(
        [SUDO, "-n", SYSTEMCTL, action, unit],
        capture_output=True, text=True, timeout=30,
    )
    return proc.returncode, (proc.stderr or proc.stdout).strip()


@app.before_request
def require_admin():
    if request.path == "/healthz":
        return None
    user = get_user()
    if not user:
        return "Unauthorized", 401
    if not is_admin() and not app.debug:
        return "Forbidden - admin group required", 403


@app.route("/healthz")
def healthz():
    return "ok", 200


@app.route("/")
def index():
    servers = load_servers()
    rows = []
    for slug, meta in servers.items():
        rows.append({
            "slug":    slug,
            "name":    meta.get("name", slug),
            "game":    meta.get("game_type", ""),
            "connect": meta.get("connect_address", ""),
            "status":  unit_status(meta["systemd_unit"]),
        })
    return render_template("list.html", user=get_user(), servers=rows)


@app.route("/server/<slug>")
def server_detail(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    status = unit_status(meta["systemd_unit"])
    return render_template("server.html", user=get_user(), s=meta, status=status)


@app.route("/server/<slug>/power", methods=["POST"])
def server_power(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    action = (request.form.get("action") or (request.json or {}).get("action") or "").strip()
    if action not in ALLOWED_POWER:
        return jsonify({"ok": False, "error": "invalid action"}), 400
    rc, msg = power(meta["systemd_unit"], action)
    if request.headers.get("Accept", "").startswith("application/json") or request.is_json:
        return jsonify({"ok": rc == 0, "rc": rc, "message": msg})
    return redirect(url_for("server_detail", slug=slug))


@app.route("/api/servers")
def api_servers():
    servers = load_servers()
    out = []
    for slug, meta in servers.items():
        status = unit_status(meta["systemd_unit"])
        out.append({
            "slug":    slug,
            "name":    meta.get("name", slug),
            "active":  status["active"],
            "connect": meta.get("connect_address", ""),
        })
    return jsonify(out)


@app.route("/api/server/<slug>/status")
def api_server_status(slug):
    servers = load_servers()
    meta = servers.get(slug)
    if not meta:
        abort(404)
    return jsonify({
        "slug":   slug,
        "name":   meta.get("name", slug),
        "status": unit_status(meta["systemd_unit"]),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("HANGAR_PORT", "5010")))
