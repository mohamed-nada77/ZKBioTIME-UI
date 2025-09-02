# auth.py
import requests
from config import BASE_URL, USERNAME, PASSWORD
from utils.state import set_token

def login():
    try:
        url = f"{BASE_URL}/api-token-auth/"
        response = requests.post(url, json={"username": USERNAME, "password": PASSWORD})
        response.raise_for_status()
        token = response.json().get("token")

        if token:
            print("[LOGIN SUCCESS] Token received:", token)
            set_token(token)
            return True
        else:
            print("[LOGIN FAIL] No token in response")
            return False
    except Exception as e:
        print("[LOGIN ERROR]", e)
        return False
