#!/usr/bin/env python
"""
测试 interest_expense 数据来源：
1. ROIC 利润表是否包含该字段
2. yfinance info 是否包含该字段
"""

import os
import requests
import yfinance as yf

ROIC_API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
ROIC_BASE = "https://api.roic.ai/v2/fundamental"

def test_roic(ticker="AAPL"):
    """检查 ROIC 利润表中是否包含 interest_expense 字段"""
    url = f"{ROIC_BASE}/income-statement/{ticker}"
    params = {"period": "quarterly", "limit": 3, "order": "DESC", "apikey": ROIC_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"❌ ROIC 请求失败: {resp.status_code}")
            return
        data = resp.json()
        first = data[0] if data else {}
        print("ROIC 利润表最新记录字段:")
        for key in first.keys():
            print(f"  {key}")
        if "interest_expense" in first or "interestExpense" in first:
            print("✅ ROIC 利润表包含 interest_expense")
        else:
            print("❌ ROIC 利润表不包含 interest_expense")
    except Exception as e:
        print(f"❌ ROIC 请求异常: {e}")

def test_yfinance(ticker="AAPL"):
    """检查 yfinance info 中是否包含 interest expense 相关字段"""
    stock = yf.Ticker(ticker)
    info = stock.info
    print("\nyfinance info 中包含 'interest' 的键:")
    found = False
    for key in info.keys():
        if 'interest' in key.lower():
            print(f"  {key}: {info[key]}")
            found = True
    if not found:
        print("  无 'interest' 相关键")
    # 也检查财务报表
    fin = stock.financials
    if fin is not None and not fin.empty:
        print("\nyfinance 年度财务报表中包含 'interest' 的行:")
        interest_rows = [idx for idx in fin.index if 'interest' in idx.lower()]
        if interest_rows:
            for row in interest_rows:
                print(f"  {row}: {fin.loc[row].to_dict()}")
        else:
            print("  无 'interest' 相关行")
    else:
        print("  年度财务报表为空")

if __name__ == "__main__":
    test_roic("AAPL")
    test_yfinance("AAPL")
