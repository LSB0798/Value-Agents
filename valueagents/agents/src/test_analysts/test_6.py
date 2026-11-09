#!/usr/bin/env python
"""
ROIC.ai API 全面测试
- 检查数据可用性和字段完整性
- 验证 TTM 合成
- 测试多股票
"""

import os
import requests
import json
import time
from datetime import datetime, timedelta
import pandas as pd

API_KEY = os.environ.get("ROIC_API_KEY", "w0W0fpmdjfiKw92Xd9J2jpY2yyqJtsbn")
BASE = "https://api.roic.ai/v2/fundamental"

# 请求间隔（秒），确保每分钟不超过5次（60/5=12秒）
REQUEST_INTERVAL = 12

def _get(endpoint: str, params: dict, retries: int = 3) -> dict | None:
    url = f"{BASE}/{endpoint}"
    params["apikey"] = API_KEY
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            # print(f"🔗 {resp.url}")
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = REQUEST_INTERVAL * (attempt + 1)
                print(f"   ⚠️  速率限制 (429)，等待 {wait} 秒后重试...")
                time.sleep(wait)
                continue
            else:
                print(f"   ⚠️  {endpoint} 返回 {resp.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ 异常: {e}")
            time.sleep(REQUEST_INTERVAL)
            continue
    print(f"   ❌ {endpoint} 多次重试失败")
    return None

def test_ticker(ticker, quarters=12):
    print(f"\n{'='*80}")
    print(f"测试 {ticker}")
    print(f"{'='*80}")

    # 1. 利润表（季度）
    income = _get(f"income-statement/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if not income:
        print("   ❌ 无法获取利润表")
        return
    print(f"✅ 利润表: {len(income)} 条记录")
    # print(f"   字段: {list(income[0].keys())}")

    time.sleep(REQUEST_INTERVAL)  # 避免连续请求

    # 2. 资产负债表（季度）
    balance = _get(f"balance-sheet/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if not balance:
        print("   ❌ 无法获取资产负债表")
        return
    print(f"✅ 资产负债表: {len(balance)} 条记录")

    time.sleep(REQUEST_INTERVAL)

    # 3. 现金流量表（季度）
    cashflow = _get(f"cash-flow/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if not cashflow:
        print("   ❌ 无法获取现金流量表")
        return
    print(f"✅ 现金流量表: {len(cashflow)} 条记录")

    time.sleep(REQUEST_INTERVAL)

    # 4. 盈利能力比率
    ratios = _get(f"ratios/profitability/{ticker}", {"period": "quarterly", "limit": quarters, "order": "DESC"})
    if ratios:
        print(f"✅ 比率: {len(ratios)} 条记录")
        # print(f"   比率字段: {list(ratios[0].keys())}")
    else:
        print("⚠️ 无法获取比率")

    time.sleep(REQUEST_INTERVAL)

    # 检查字段完整性：选取最新一条
    if income and balance and cashflow:
        inc_row = income[0]
        bal_row = balance[0]
        cf_row = cashflow[0]

        # 定义关键字段映射
        required_fields = {
            "收入": "is_sales_revenue_turnover",
            "净收入": "is_net_income",
            "营业利润(EBIT)": "is_oper_income",
            "利息费用": "is_int_expense",
            "毛利润": "is_gross_profit",
            "研发费用": "is_operating_expenses_r_and_d",
            "总资产": "bs_tot_asset",
            "总负债": "bs_tot_liab",
            "股东权益": "bs_total_equity",
            "总债务": "bs_total_debt",
            "现金及等价物": "bs_cash",
            "流动资产": "bs_current_assets",
            "流动负债": "bs_current_liab",
            "长期债务": "bs_long_term_debt",
            "自由现金流": "cf_free_cash_flow",
            "资本支出": "cf_capex",  # 可能不存在
            "折旧摊销": "cf_dep_amor",  # 可能不存在
        }

        print("\n📊 最新报告期字段值:")
        for label, field in required_fields.items():
            value = inc_row.get(field) or bal_row.get(field) or cf_row.get(field)
            if value is not None:
                print(f"   {label:>10}: {value:,.0f}")
            else:
                print(f"   {label:>10}: ⚠️ 缺失")

        # 检查比率最新值
        if ratios:
            rat_row = ratios[0]
            print("\n📈 最新比率:")
            print(f"   ROIC: {rat_row.get('return_on_inv_capital'):.2f}%")
            print(f"   ROE: {rat_row.get('return_com_eqy'):.2f}%")
            print(f"   毛利率: {rat_row.get('gross_margin'):.2f}%")
            print(f"   营业利润率: {rat_row.get('oper_margin'):.2f}%")
            print(f"   净利率: {rat_row.get('profit_margin'):.2f}%")

    # TTM 合成测试（如果能获取足够多季度）
    if len(income) >= 4 and len(balance) >= 4 and len(cashflow) >= 4:
        print("\n🔬 TTM 合成测试 (最近4个季度，报告期为最新季度末)")
        inc_df = pd.DataFrame(income[:4])
        bal_df = pd.DataFrame(balance[:4])
        cf_df = pd.DataFrame(cashflow[:4])

        # 单季值求和
        ttm_revenue = inc_df['is_sales_revenue_turnover'].sum()
        ttm_net_income = inc_df['is_net_income'].sum()
        if 'is_oper_income' in inc_df.columns:
            ttm_ebit = inc_df['is_oper_income'].sum()
        else:
            ttm_ebit = None
        if 'cf_free_cash_flow' in cf_df.columns:
            ttm_fcf = cf_df['cf_free_cash_flow'].sum()
        else:
            ttm_fcf = None

        latest_bal = bal_df.iloc[0]
        total_assets = latest_bal.get('bs_tot_asset')
        total_equity = latest_bal.get('bs_total_equity')
        total_debt = latest_bal.get('bs_total_debt')

        print(f"   TTM 收入: {ttm_revenue:,.0f}")
        print(f"   TTM 净收入: {ttm_net_income:,.0f}")
        print(f"   TTM EBIT: {ttm_ebit if ttm_ebit is not None else 'N/A'}")
        print(f"   TTM FCF: {ttm_fcf if ttm_fcf is not None else 'N/A'}")
        if total_equity:
            roe_ttm = ttm_net_income / total_equity
            print(f"   TTM ROE: {roe_ttm:.2%}")
        if total_assets:
            roa_ttm = ttm_net_income / total_assets
            print(f"   TTM ROA: {roa_ttm:.2%}")

        print("   ✅ TTM 合成成功")

    # 检查历史数据深度
    print(f"\n📅 历史数据范围: 从 {income[-1]['fiscal_year']} 到 {income[0]['fiscal_year']}")

if __name__ == "__main__":
    print("ROIC.ai 全面测试")
    for ticker in ["AAPL", "MSFT", "TSLA"]:
        test_ticker(ticker, quarters=12)
        # 每个 ticker 测试后多等几秒，让速率限制完全重置
        time.sleep(REQUEST_INTERVAL * 2)
