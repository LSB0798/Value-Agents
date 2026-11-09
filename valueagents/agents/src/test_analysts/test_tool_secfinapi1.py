import requests

API_KEY = "sk_56bee8645c5fa75fdf9a2a574ce064ad7083fe69a9302da46cbb1aed9ce4"   # 替换为完整密钥
TICKER = "MSFT"

url = f"https://www.secfinapi.com/v1/company/{TICKER}/income-statement"
headers = {
    "X-API-Key": API_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}
params = {"period": "annual", "limit": 5}

resp = requests.get(url, headers=headers, params=params)
print(f"状态码: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())
else:
    print(resp.text[:500])


