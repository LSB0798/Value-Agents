#!/usr/bin/env python
"""
FMP 探查脚本（limit=5 兼容版）
"""
import requests
import json

API_KEY = "jJBfwAmaiV3mUfBhZ8IecaDzmZgVr8lo"
BASE = "https://financialmodelingprep.com/stable"


def test_endpoint(name: str, url: str, params: dict):
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}")
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"🔗 {resp.url}")
        print(f"   HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                print(f"   ✅ 返回 {len(data)} 条记录")
                if data:
                    print(f"   字段: {list(data[0].keys())}")
                    # 打印最近 5 条的关键字段
                    print(f"\n   {'date':<12} {'period':<8} {'revenue':>18} {'netIncome':>18}")
                    print(f"   {'-'*60}")
                    for row in data[:5]:
                        date = row.get("date", "")
                        period = row.get("period", "")
                        rev = row.get("revenue", "")
                        ni = row.get("netIncome", "")
                        rev_str = f"{rev:>18,.0f}" if isinstance(rev, (int, float)) else f"{str(rev):>18}"
                        ni_str = f"{ni:>18,.0f}" if isinstance(ni, (int, float)) else f"{str(ni):>18}"
                        print(f"   {date:<12} {period:<8} {rev_str} {ni_str}")
            elif isinstance(data, dict):
                print(f"   ✅ dict, keys: {list(data.keys())[:10]}")
        else:
            print(f"   ❌ {resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")


if __name__ == "__main__":
    # 1) Company Profile
    test_endpoint(
        "[1] Company Profile",
        f"{BASE}/profile",
        {"symbol": "AAPL", "apikey": API_KEY}
    )

    # 2) Income Statement (Quarterly, limit=5)
    test_endpoint(
        "[2] Income Statement (Quarterly, limit=5)",
        f"{BASE}/income-statement",
        {"symbol": "AAPL", "period": "quarter", "limit": 5, "apikey": API_KEY}
    )

    # 3) Balance Sheet (Quarterly, limit=5)
    test_endpoint(
        "[3] Balance Sheet (Quarterly, limit=5)",
        f"{BASE}/balance-sheet-statement",
        {"symbol": "AAPL", "period": "quarter", "limit": 5, "apikey": API_KEY}
    )

    # 4) Cash Flow (Quarterly, limit=5)
    test_endpoint(
        "[4] Cash Flow (Quarterly, limit=5)",
        f"{BASE}/cash-flow-statement",
        {"symbol": "AAPL", "period": "quarter", "limit": 5, "apikey": API_KEY}
    )

    # 5) Ratios (Quarterly, limit=5) —— 修正端点路径
    test_endpoint(
        "[5] Ratios (Quarterly, limit=5)",
        f"{BASE}/ratios",
        {"symbol": "AAPL", "period": "quarter", "limit": 5, "apikey": API_KEY}
    )

    # 6) Key Metrics (Quarterly, limit=5)
    test_endpoint(
        "[6] Key Metrics (Quarterly, limit=5)",
        f"{BASE}/key-metrics",
        {"symbol": "AAPL", "period": "quarter", "limit": 5, "apikey": API_KEY}
    )