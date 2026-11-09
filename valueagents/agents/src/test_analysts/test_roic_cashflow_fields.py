#!/usr/bin/env python
"""
测试 ROIC 现金流量表是否提供股份发行/回购相关字段
"""

import os
import requests
import json

ROIC_API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
ROIC_BASE = "https://api.roic.ai/v2/fundamental"

def roic_request(endpoint, params):
    url = f"{ROIC_BASE}/{endpoint}"
    params["apikey"] = ROIC_API_KEY
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"⚠️ 状态码 {resp.status_code}: {resp.text[:200]}")
        return None

def test_cashflow_fields(ticker="AAPL"):
    print(f"\n测试 {ticker} 现金流量表字段")
    cashflow = roic_request(f"cash-flow/{ticker}", {"period": "quarterly", "limit": 2, "order": "DESC"})
    if not cashflow:
        print("❌ 无法获取现金流量表数据")
        return

    print(f"✅ 获取到 {len(cashflow)} 条记录")
    first = cashflow[0]
    print("\n所有字段名:")
    for key in sorted(first.keys()):
        print(f"  {key}")

    # 检查与股份发行/回购相关的字段
    keywords = ['share', 'issuance', 'repurchase', 'equity', 'stock', 'capital', 'common']
    matched = []
    for key in first.keys():
        if any(kw in key.lower() for kw in keywords):
            matched.append(key)

    if matched:
        print("\n🔍 找到疑似股份发行/回购相关的字段:")
        for key in matched:
            value = first.get(key)
            print(f"  {key}: {value}")
    else:
        print("\n⚠️ 未找到明确的股份发行/回购字段")

if __name__ == "__main__":
    test_cashflow_fields("AAPL")
    test_cashflow_fields("MSFT")
