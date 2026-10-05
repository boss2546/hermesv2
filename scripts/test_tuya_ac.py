import time
import hmac
import hashlib
import json
import requests

CLIENT_ID = "skyyg375tcfaqj9war7j"
SECRET = "2b5890904db34ba190cebb92a98f62dc"
ENDPOINT = "https://openapi-sg.iotbing.com"
HUB_ID = "a3a0871e8e9cc9ecfbivya"
REMOTE_ID = "a35a4e0b12b02aa750ceh4"

def get_signature(method, path, body="", access_token="", t=""):
    content_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    string_to_sign = f"{method.upper()}\n{content_hash}\n\n{path}"
    sign_payload = f"{CLIENT_ID}{access_token}{t}{string_to_sign}"
    return hmac.new(SECRET.encode('utf-8'), sign_payload.encode('utf-8'), hashlib.sha256).hexdigest().upper()

def get_token():
    t = str(int(time.time() * 1000))
    path = "/v1.0/token?grant_type=1"
    sign = get_signature("GET", path, "", "", t)
    headers = {
        "client_id": CLIENT_ID,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256"
    }
    r = requests.get(f"{ENDPOINT}{path}", headers=headers)
    data = r.json()
    if data.get("success"):
        return data["result"]["access_token"]
    raise Exception(f"Token failed: {data}")

def request_tuya(token, method, path, data=None):
    t = str(int(time.time() * 1000))
    body = json.dumps(data) if data is not None and method != "GET" else ""
    sign = get_signature(method, path, body, token, t)
    headers = {
        "client_id": CLIENT_ID,
        "access_token": token,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256"
    }
    if body:
        headers["Content-Type"] = "application/json"
    url = f"{ENDPOINT}{path}"
    if method == "GET":
        r = requests.get(url, headers=headers)
    else:
        r = requests.post(url, headers=headers, data=body)
    return r.json()

def main():
    token = get_token()
    info = request_tuya(token, "GET", f"/v1.0/infrareds/{HUB_ID}/remotes/{REMOTE_ID}")
    print("=== Remote Info ===")
    print(json.dumps(info, indent=2))

    rules = request_tuya(token, "GET", f"/v1.0/infrareds/{HUB_ID}/remotes/{REMOTE_ID}/rules")
    print("=== Remote Rules ===")
    print(json.dumps(rules, indent=2))

if __name__ == "__main__":
    main()
