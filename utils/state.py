# utils/state.py
_token = None  # Only declared once

def set_token(t):
    global _token
    _token = t
    print("[DEBUG] Token SET:", _token)

def get_token():
    print("[DEBUG] Token GET:", _token)
    return _token

def get_auth_headers():
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {_token}"  # or 'Bearer' if needed
    }
    print("[DEBUG] Auth Headers:", headers)
    return headers
