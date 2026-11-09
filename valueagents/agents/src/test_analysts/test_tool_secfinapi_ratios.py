#!/usr/bin/env python
import requests

API_KEY = "sk_56bee8645c5fa75fdf9a2a574ce064ad7083fe69a9302da46cbb1aed9ce4"
TICKER = "AAPL"
BASE_URL = "https://www.secfinapi.com/v1/company"

endpoints = [
    f"/{TICKER}/metrics",
    f"/{TICKER}/ratios",
    f"/{TICKER}/financial-ratios",
    f"/{TICKER}/key-metrics",
    f"/{TICKER}/fundamental-ratios",
]

headers = {"X-API-Key": API_KEY, "Accept": "application/json"}

for ep in endpoints:
    url = f"{BASE_URL}{ep}"
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"{ep}: {resp.status_code}")
    if resp.status_code == 200:
        print(resp.json().keys())
