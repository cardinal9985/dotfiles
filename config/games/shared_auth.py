from flask import request

def get_user():
    return request.headers.get("Remote-User", "").strip()
