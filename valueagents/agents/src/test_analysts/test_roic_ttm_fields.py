#!/usr/bin/env python
"""
测试 ROIC API 是否提供 earnings_per_share、free_cash_flow_per_share、
price_to_sales_ratio、free_cash_flow_yield 等字段，并列出所有可用字段。
"""

import os
import requests
import json
import time
from pprint import pprint

ROIC_API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
ROIC_BASE = "https://api.roic.ai/v2/fundamental"

def roic_request(endpoint, params):
    url = f"{ROIC_BASE}/{endpoint}"
    params["apikey"] = ROIC_API_KEY
    print(f"🔗 请求: {url}?{params}")
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"⚠️ 状态码 {resp.status_code}: {resp.text[:200]}")
        return None

def test_ticker(ticker="AAPL", quarters=10):
    print(f"\n{'='*80}")
    print(f"测试 {ticker} 的季度数据字段")
    print(f"{'='*80}")

    # 1. 利润表 (季度)
    income = roic_request(f"income-statement/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if income:
        print("\n📋 利润表字段 (第一条记录的键):")
        first = income[0]
        for key in first.keys():
            print(f"  {key}")
        # 检查特定字段
        check_fields = ['eps', 'diluted_eps', 'is_sales_revenue_turnover', 'is_net_income', 'is_oper_income', 'ebitda', 'gross_margin', 'oper_margin', 'profit_margin']
        print("\n🔍 检查利润表关键字段:")
        for f in check_fields:
            val = first.get(f)
            print(f"  {f}: {val if val is not None else '❌ 缺失'}")

    time.sleep(2)

    # 2. 资产负债表 (季度)
    balance = roic_request(f"balance-sheet/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if balance:
        print("\n📋 资产负债表字段 (第一条记录的键):")
        first = balance[0]
        for key in first.keys():
            print(f"  {key}")
        check_fields = ['bs_sh_out', 'bs_total_equity', 'bs_tot_asset', 'bs_tot_liab', 'bs_cash_near_cash_item', 'bs_cur_asset_report', 'bs_cur_liab', 'bs_long_term_debt', 'bs_short_term_debt']
        print("\n🔍 检查资产负债表关键字段:")
        for f in check_fields:
            val = first.get(f)
            print(f"  {f}: {val if val is not None else '❌ 缺失'}")

    time.sleep(2)

    # 3. 现金流量表 (季度)
    cashflow = roic_request(f"cash-flow/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if cashflow:
        print("\n📋 现金流量表字段 (第一条记录的键):")
        first = cashflow[0]
        for key in first.keys():
            print(f"  {key}")
        check_fields = ['cf_free_cash_flow', 'cf_cap_expenditures', 'cf_depr_amort']
        print("\n🔍 检查现金流量表关键字段:")
        for f in check_fields:
            val = first.get(f)
            print(f"  {f}: {val if val is not None else '❌ 缺失'}")

    time.sleep(2)

    # 4. 比率 (季度)
    ratios = roic_request(f"ratios/profitability/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if ratios:
        print("\n📋 比率字段 (第一条记录的键):")
        first = ratios[0]
        for key in first.keys():
            print(f"  {key}")
        check_fields = ['return_on_inv_capital', 'return_com_eqy', 'gross_margin', 'oper_margin', 'profit_margin']
        print("\n🔍 检查比率关键字段:")
        for f in check_fields:
            val = first.get(f)
            print(f"  {f}: {val if val is not None else '❌ 缺失'}")

    # 总结：所需字段是否可直接获得
    print("\n" + "="*80)
    print("📌 结论:")
    print("- earnings_per_share: ROIC 利润表提供 'eps' 字段（季度 EPS）。TTM EPS 需将最近4个季度的净收入累加并除以最新流通股（bs_sh_out）。")
    print("- free_cash_flow_per_share: ROIC 现金流量表提供 'cf_free_cash_flow'（季度 FCF）。TTM FCF 需累加4个季度，再除以流通股。")
    print("- price_to_sales_ratio: ROIC 不直接提供，需要从 yfinance 获取市值，除以 TTM 营收。")
    print("- free_cash_flow_yield: 需从 yfinance 获取市值，TTM FCF 除以市值。")
    print("- book_value_per_share: 可使用资产负债表中的 bs_total_equity 除以 bs_sh_out（时点值）。")
    print("- price_to_book_ratio: 需从 yfinance 获取市值，除以 bs_total_equity。")
    print("- enterprise_value: 需从 yfinance 获取市值，加上总债务（bs_long_term_debt + bs_short_term_debt）减去现金（bs_cash_near_cash_item）。")

if __name__ == "__main__":
    test_ticker("AAPL")
