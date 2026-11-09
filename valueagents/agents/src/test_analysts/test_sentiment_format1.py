#!/usr/bin/env python
"""
直接调用 Alpha Vantage 新闻 API，打印原始 JSON，检查情感标签字段
"""

import os
import requests
import json

API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "LEPNUFM9ZGGRXWDR")
TICKER = "AAPL"

def test_raw_alpha_vantage(ticker):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "limit": 5,
        "apikey": API_KEY,
        "sort": "LATEST"
    }
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    print(f"请求 URL: {resp.url}")
    print(f"响应状态: {resp.status_code}")
    print("返回的 JSON 结构（第一条新闻）:")
    if "feed" in data and data["feed"]:
        first_article = data["feed"][0]
        print(json.dumps(first_article, indent=2, ensure_ascii=False))
    else:
        print(data)

if __name__ == "__main__":
    test_raw_alpha_vantage("AAPL")
