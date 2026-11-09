#!/usr/bin/env python
"""
完整测试 SECfinAPI 的数据覆盖和计算能力
目标：验证是否能获取 gross_margin, operating_margin, debt_to_equity
"""

import os
import json
import requests
from pprint import pprint

API_KEY = "sk_56bee8645c5fa75fdf9a2a574ce064ad7083fe69a9302da46cbb1aed9ce4"
TICKER = "MSFT"
BASE_URL = "https://www.secfinapi.com/v1/company"

def fetch_statement(endpoint, period="annual", limit=5):
    """获取财务报表"""
    url = f"{BASE_URL}/{TICKER}/{endpoint}"
    headers = {
        "X-API-Key": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    params = {"period": period, "limit": limit}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def extract_data(statement_data):
    """从返回的JSON中提取数据字典"""
    return statement_data.get("data", {})

def get_years(data_dict):
    """获取所有年份（从第一个数据项中提取键）"""
    years = set()
    for v in data_dict.values():
        if isinstance(v, dict):
            years.update(v.keys())
    return sorted(years, reverse=True)

def calc_metrics(income_data, balance_data, cashflow_data):
    revenue = income_data.get("Revenue", {})
    gross_profit = income_data.get("GrossProfit", {})
    operating_income = income_data.get("OperatingIncome", {})
    
    total_debt = balance_data.get("TotalDebt", {}) if balance_data else {}
    # 尝试多个可能的权益字段名
    equity = balance_data.get("TotalEquity", {}) or balance_data.get("StockholdersEquity", {})
    
    years = set(revenue.keys()) & set(gross_profit.keys()) & set(operating_income.keys())
    if balance_data:
        years &= set(total_debt.keys()) & set(equity.keys())
    years = sorted(years, reverse=True)[:5]
    
    results = {}
    for yr in years:
        rev = revenue.get(yr)
        gp = gross_profit.get(yr)
        oi = operating_income.get(yr)
        debt = total_debt.get(yr)
        eq = equity.get(yr)
        
        gross_margin = gp / rev if (rev and gp) else None
        operating_margin = oi / rev if (rev and oi) else None
        debt_to_equity = debt / eq if (debt and eq and eq != 0) else None
        
        results[yr] = {
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "debt_to_equity": debt_to_equity,
        }
    return results

def main():
    print(f"🔍 获取 {TICKER} 的财务报表数据...")
    
    # 获取利润表
    print("\n📊 获取利润表...")
    income_data = fetch_statement("income-statement", limit=5)
    income_dict = extract_data(income_data)
    print(f"✅ 利润表字段: {list(income_dict.keys())}")
    
    # 获取资产负债表
    print("\n📊 获取资产负债表...")
    try:
        balance_data = fetch_statement("balance-sheet", limit=5)
        balance_dict = extract_data(balance_data)
        print(f"✅ 资产负债表字段: {list(balance_dict.keys())}")
    except Exception as e:
        print(f"⚠️ 资产负债表获取失败: {e}")
        balance_dict = {}
    
    # 获取现金流量表（可选）
    print("\n📊 获取现金流量表...")
    try:
        cashflow_data = fetch_statement("cash-flow", limit=5)
        cashflow_dict = extract_data(cashflow_data)
        print(f"✅ 现金流量表字段: {list(cashflow_dict.keys())}")
    except Exception as e:
        print(f"⚠️ 现金流量表获取失败: {e}")
        cashflow_dict = {}
    
    # 计算比率
    print("\n📈 计算财务比率...")
    results = calc_metrics(income_dict, balance_dict, cashflow_dict)
    print("\n年份 | Gross Margin | Operating Margin | Debt/Equity")
    print("-----|--------------|------------------|------------")
    for yr, vals in sorted(results.items(), reverse=True):
        gm = f"{vals['gross_margin']:.2%}" if vals['gross_margin'] is not None else "N/A"
        om = f"{vals['operating_margin']:.2%}" if vals['operating_margin'] is not None else "N/A"
        de = f"{vals['debt_to_equity']:.2f}" if vals['debt_to_equity'] is not None else "N/A"
        print(f"{yr} | {gm:>13} | {om:>16} | {de:>10}")
    
    # 展示原始数据示例（利润表第一个字段）
    if income_dict:
        first_key = list(income_dict.keys())[0]
        print(f"\n📋 利润表示例数据（{first_key}）:")
        print(json.dumps(income_dict[first_key], indent=2)[:500] + "...")
    
    # 检查是否直接提供这些比率（通过其他端点？）
    # 尝试获取 metrics 端点（如果存在）
    try:
        print("\n🔍 尝试获取 metrics 端点...")
        url = f"{BASE_URL}/{TICKER}/metrics"
        headers = {"X-API-Key": API_KEY, "Accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            metrics_data = resp.json()
            print("✅ metrics 端点可用，返回字段:")
            print(list(metrics_data.keys())[:10])
        else:
            print(f"⚠️ metrics 端点返回状态码 {resp.status_code}")
    except:
        print("⚠️ metrics 端点不可用")

if __name__ == "__main__":
    main()