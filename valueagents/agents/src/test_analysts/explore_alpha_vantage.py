#!/usr/bin/env python
"""
探索 Alpha Vantage API 获取季度财务数据（尝试不同参数组合）。
"""

import os
import time
import requests
import json
from pprint import pprint

API_KEY = "LEPNUFM9ZGGRXWDR"
BASE_URL = "https://www.alphavantage.co/query"

def call_api(params):
    params['apikey'] = API_KEY
    print(f"\n🔍 调用: {params['function']} with params: {params}")
    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        data = response.json()
        if "Error Message" in data:
            print(f"❌ 错误: {data['Error Message']}")
            return None
        if "Information" in data and "API key" in data.get("Information", ""):
            print(f"⚠️ 信息: {data['Information']}")
            # 可能表示需要付费或参数错误
        if "Note" in data:
            print(f"⚠️ 速率限制: {data['Note']}")
            return None
        return data
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_income_statement():
    """测试 INCOME_STATEMENT 端点，尝试添加 period 参数"""
    print("\n" + "="*60)
    print("2. 测试 INCOME_STATEMENT（尝试 period=quarter）")
    # 尝试不同参数组合
    for period in [None, "quarter", "annual", "ttm"]:
        params = {"function": "INCOME_STATEMENT", "symbol": "AAPL"}
        if period:
            params["period"] = period
        data = call_api(params)
        if not data:
            continue
        if "quarterlyReports" in data:
            print(f"✅ 成功获取季度数据（使用 period={period}）")
            pprint(data["quarterlyReports"][0])
            return
        elif "annualReports" in data:
            print(f"⚠️ 仅获取到年度数据（period={period}）")
        else:
            print(f"❌ 未找到 reports，返回键: {data.keys()}")
    print("❌ 所有尝试均失败")

def test_earnings():
    """测试 EARNINGS 端点"""
    print("\n" + "="*60)
    print("3. 测试 EARNINGS 端点")
    data = call_api({"function": "EARNINGS", "symbol": "AAPL"})
    if data and "quarterlyEarnings" in data:
        print("✅ 获取到季度 EPS 数据")
        pprint(data["quarterlyEarnings"][:2])
    else:
        print("❌ 未找到 quarterlyEarnings")

def main():
    print("🔍 重新探索 Alpha Vantage 季度数据...")
    test_income_statement()
    time.sleep(1)
    test_earnings()

if __name__ == "__main__":
    main()
