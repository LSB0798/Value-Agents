#!/usr/bin/env python
"""
测试 ROIC API 返回的字段名，验证与 api.py 中使用的字段是否一致
"""

import os
import json
import requests
import time
from pprint import pprint

# 使用与 api.py 相同的 API Key 和 Base URL
ROIC_API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
ROIC_BASE = "https://api.roic.ai/v2/fundamental"

def roic_request(endpoint, params, delay=12):
    url = f"{ROIC_BASE}/{endpoint}"
    params["apikey"] = ROIC_API_KEY
    print(f"🔗 请求: {url}?{params}")
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ 状态码 {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

def print_fields(data, title, max_items=3):
    if not data:
        print(f"❌ {title} 无数据")
        return
    print(f"\n📋 {title} (共 {len(data)} 条记录)")
    # 显示第一条记录的字段及示例值
    first = data[0]
    print(f"字段名及示例值 (第一条):")
    for key, value in first.items():
        # 截断长字符串
        if isinstance(value, str) and len(value) > 80:
            value = value[:80] + "..."
        print(f"  {key}: {repr(value)}")
    # 如果有多条，再显示第二条和第三条的日期/年份等关键字段
    if len(data) > 1:
        print("\n后续记录的部分关键字段:")
        for idx, item in enumerate(data[1:max_items], start=2):
            print(f"  记录 {idx}: date={item.get('date')}, fiscal_year={item.get('fiscal_year')}")

def test_ticker(ticker="AAPL"):
    print(f"\n{'='*80}")
    print(f"测试股票: {ticker}")
    print(f"{'='*80}")

    # 1. 利润表 (季度)
    print("\n--- 利润表 (季度) ---")
    income = roic_request("income-statement/AAPL", {"period": "quarterly", "limit": 3, "order": "DESC"})
    if income:
        print_fields(income, "利润表")
    time.sleep(2)

    # 2. 资产负债表 (季度)
    print("\n--- 资产负债表 (季度) ---")
    balance = roic_request("balance-sheet/AAPL", {"period": "quarterly", "limit": 3, "order": "DESC"})
    if balance:
        print_fields(balance, "资产负债表")
    time.sleep(2)

    # 3. 现金流量表 (季度)
    print("\n--- 现金流量表 (季度) ---")
    cashflow = roic_request("cash-flow/AAPL", {"period": "quarterly", "limit": 3, "order": "DESC"})
    if cashflow:
        print_fields(cashflow, "现金流量表")
    time.sleep(2)

    # 4. 比率 (季度)
    print("\n--- 盈利能力比率 (季度) ---")
    ratios = roic_request("ratios/profitability/AAPL", {"period": "quarterly", "limit": 3, "order": "DESC"})
    if ratios:
        print_fields(ratios, "比率")
    time.sleep(2)

    # 5. 年度数据（可选，用于对比）
    print("\n--- 利润表 (年度) ---")
    income_annual = roic_request("income-statement/AAPL", {"period": "annual", "limit": 3, "order": "DESC"})
    if income_annual:
        print_fields(income_annual, "年度利润表")

if __name__ == "__main__":
    test_ticker("AAPL")
