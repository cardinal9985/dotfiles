import os
import sqlite3
import time
import urllib.request
import urllib.parse
import json
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, g, jsonify

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/requests.db")

TMDB_TOKEN_FILE = os.environ.get("TMDB_TOKEN_FILE", "")
if TMDB_TOKEN_FILE and os.path.isfile(TMDB_TOKEN_FILE):
    TMDB_TOKEN = open(TMDB_TOKEN_FILE).read().strip()
else:
    TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "")

NTFY_TOKEN_FILE = os.environ.get("NTFY_TOKEN_FILE", "")
if NTFY_TOKEN_FILE and os.path.isfile(NTFY_TOKEN_FILE):
    NTFY_TOKEN = open(NTFY_TOKEN_FILE).read().strip()
else:
    NTFY_TOKEN = os.environ.get("NTFY_TOKEN", "")

IGDB_CLIENT_ID_FILE = os.environ.get("IGDB_CLIENT_ID_FILE", "")
if IGDB_CLIENT_ID_FILE and os.path.isfile(IGDB_CLIENT_ID_FILE):
    IGDB_CLIENT_ID = open(IGDB_CLIENT_ID_FILE).read().strip()
else:
    IGDB_CLIENT_ID = os.environ.get("IGDB_CLIENT_ID", "")

IGDB_CLIENT_SECRET_FILE = os.environ.get("IGDB_CLIENT_SECRET_FILE", "")
if IGDB_CLIENT_SECRET_FILE and os.path.isfile(IGDB_CLIENT_SECRET_FILE):
    IGDB_CLIENT_SECRET = open(IGDB_CLIENT_SECRET_FILE).read().strip()
else:
    IGDB_CLIENT_SECRET = os.environ.get("IGDB_CLIENT_SECRET", "")

NTFY_URL = os.environ.get("NTFY_URL", "http://host.containers.internal:8090")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "ishimura-requests")

# IGDB OAuth2 token cache
_igdb_token = {"access_token": "", "expires_at": 0}

# Rate limiting: max 10 requests per user per hour
rate_limit = defaultdict(list)
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 3600

VALID_TYPES = {"Movie", "Show", "Music", "Book", "Game"}
VALID_STATUSES = {"pending", "approved", "completed", "denied"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def is_rate_limited(user):
    now = time.time()
    rate_limit[user] = [t for t in rate_limit[user] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limit[user]) >= RATE_LIMIT_MAX:
        return True
    rate_limit[user].append(now)
    return False


def get_user(req):
    return req.headers.get("Remote-User", "").strip()


def is_admin(req):
    groups = req.headers.get("Remote-Groups", "")
    return "admins" in [grp.strip() for grp in groups.split(",")]


def render_index(user, admin, error=None, success=None):
    db = get_db()
    if admin:
        rows = db.execute(
            "SELECT * FROM requests ORDER BY created_at DESC"
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM requests WHERE username = ? ORDER BY created_at DESC",
            (user,),
        ).fetchall()
    return render_template(
        "index.html", user=user, admin=admin, requests=rows,
        error=error, success=success,
    )


def api_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def search_tmdb(query, media_type):
    endpoint = "movie" if media_type == "Movie" else "tv"
    url = "https://api.themoviedb.org/3/search/{}?{}".format(
        endpoint, urllib.parse.urlencode({"query": query})
    )
    data = api_get(url, {"Authorization": "Bearer " + TMDB_TOKEN})
    results = []
    for item in data.get("results", [])[:8]:
        if media_type == "Movie":
            title = item.get("title", "")
            year = (item.get("release_date") or "")[:4]
        else:
            title = item.get("name", "")
            year = (item.get("first_air_date") or "")[:4]
        results.append({
            "title": title,
            "year": year,
            "description": (item.get("overview") or "")[:120],
        })
    return results


def search_openlibrary(query):
    url = "https://openlibrary.org/search.json?{}".format(
        urllib.parse.urlencode({"q": query, "limit": 8})
    )
    data = api_get(url)
    results = []
    for doc in data.get("docs", [])[:8]:
        authors = ", ".join(doc.get("author_name", [])[:2])
        year = str(doc.get("first_publish_year", ""))
        results.append({
            "title": doc.get("title", ""),
            "year": year,
            "description": authors,
        })
    return results


def search_musicbrainz(query):
    url = "https://musicbrainz.org/ws/2/release-group/?{}".format(
        urllib.parse.urlencode({"query": query, "limit": 8, "fmt": "json"})
    )
    data = api_get(url, {"User-Agent": "IshimuraRequests/1.0"})
    results = []
    for rg in data.get("release-groups", [])[:8]:
        artists = ", ".join(
            c.get("name", "") for c in rg.get("artist-credit", [])
            if isinstance(c, dict)
        )
        year = (rg.get("first-release-date") or "")[:4]
        rg_type = rg.get("primary-type", "")
        results.append({
            "title": rg.get("title", ""),
            "year": year,
            "description": "{} — {}".format(artists, rg_type) if rg_type else artists,
        })
    return results


def get_igdb_token():
    now = time.time()
    if _igdb_token["access_token"] and now < _igdb_token["expires_at"] - 60:
        return _igdb_token["access_token"]
    params = urllib.parse.urlencode({
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }).encode()
    req = urllib.request.Request("https://id.twitch.tv/oauth2/token", data=params, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    _igdb_token["access_token"] = data["access_token"]
    _igdb_token["expires_at"] = now + data.get("expires_in", 3600)
    return _igdb_token["access_token"]


def search_igdb(query):
    token = get_igdb_token()
    body = 'search "{}"; fields name,first_release_date,summary,cover.url; limit 8;'.format(
        query.replace('"', '\\"')
    )
    req = urllib.request.Request(
        "https://api.igdb.com/v4/games",
        data=body.encode(),
        headers={
            "Client-ID": IGDB_CLIENT_ID,
            "Authorization": "Bearer " + token,
        },
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    results = []
    for item in data[:8]:
        title = item.get("name", "")
        release = item.get("first_release_date")
        year = time.strftime("%Y", time.gmtime(release)) if release else ""
        summary = (item.get("summary") or "")[:120]
        results.append({
            "title": title,
            "year": year,
            "description": summary,
        })
    return results


@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def index():
    user = get_user(request)
    if not user:
        return "Unauthorized: no Remote-User header", 401
    return render_index(user, is_admin(request))


@app.route("/search")
def search():
    user = get_user(request)
    if not user:
        return jsonify([]), 401

    query = request.args.get("q", "").strip()
    media_type = request.args.get("type", "").strip()

    if not query or len(query) < 2 or media_type not in VALID_TYPES:
        return jsonify([])

    try:
        if media_type in ("Movie", "Show"):
            if not TMDB_TOKEN:
                return jsonify([])
            results = search_tmdb(query, media_type)
        elif media_type == "Book":
            results = search_openlibrary(query)
        elif media_type == "Music":
            results = search_musicbrainz(query)
        elif media_type == "Game":
            if not IGDB_CLIENT_ID or not IGDB_CLIENT_SECRET:
                return jsonify([])
            results = search_igdb(query)
        else:
            results = []
    except Exception:
        results = []

    return jsonify(results)


@app.route("/request", methods=["POST"])
def submit_request():
    user = get_user(request)
    if not user:
        return "Unauthorized", 401

    admin = is_admin(request)

    if is_rate_limited(user):
        return render_index(user, admin, error="Too many requests. Please try again later.")

    req_type = request.form.get("type", "").strip()
    title = request.form.get("title", "").strip()
    notes = request.form.get("notes", "").strip()
    platform = request.form.get("platform", "").strip()

    if req_type not in VALID_TYPES:
        return render_index(user, admin, error="Invalid request type.")
    if not title or len(title) > 200:
        return render_index(user, admin, error="Title is required (max 200 characters).")
    if req_type == "Game" and platform:
        notes = "[{}] {}".format(platform, notes) if notes else "[{}]".format(platform)
    if len(notes) > 500:
        notes = notes[:500]

    db = get_db()
    db.execute(
        "INSERT INTO requests (username, type, title, notes) VALUES (?, ?, ?, ?)",
        (user, req_type, title, notes or None),
    )
    db.commit()

    try:
        if NTFY_TOKEN:
            ntfy_url = "{}/{}".format(NTFY_URL, NTFY_TOPIC)
            message = "{} requested {}: {}".format(user, req_type.lower(), title)
            ntfy_req = urllib.request.Request(
                ntfy_url,
                data=message.encode(),
                headers={
                    "Authorization": "Bearer " + NTFY_TOKEN,
                    "Title": "New {} request".format(req_type.lower()),
                    "Tags": req_type.lower(),
                },
                method="POST",
            )
            urllib.request.urlopen(ntfy_req, timeout=5)
    except Exception:
        pass

    return redirect(url_for("index"))


@app.route("/status/<int:req_id>", methods=["POST"])
def update_status(req_id):
    user = get_user(request)
    if not user or not is_admin(request):
        return "Forbidden", 403

    new_status = request.form.get("status", "").strip()
    if new_status not in VALID_STATUSES:
        return "Invalid status", 400

    db = get_db()
    db.execute("UPDATE requests SET status = ? WHERE id = ?", (new_status, req_id))
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:req_id>", methods=["POST"])
def delete_request(req_id):
    user = get_user(request)
    if not user or not is_admin(request):
        return "Forbidden", 403

    db = get_db()
    db.execute("DELETE FROM requests WHERE id = ?", (req_id,))
    db.commit()
    return redirect(url_for("index"))


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
