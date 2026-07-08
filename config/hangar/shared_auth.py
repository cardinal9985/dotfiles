from flask import request

def get_user():
    return request.headers.get("Remote-User", "").strip()

def get_groups():
    raw = request.headers.get("Remote-Groups", "")
    return [g.strip() for g in raw.split(",") if g.strip()]

def is_admin():
    return "admins" in get_groups()
