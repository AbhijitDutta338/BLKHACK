import requests
from config import BASE_URL

def post(endpoint, payload):
    try:
        r = requests.post(f"{BASE_URL}/{endpoint}", json=payload)
        return r.status_code, r.json()
    except Exception as e:
        return 500, {"error": str(e)}