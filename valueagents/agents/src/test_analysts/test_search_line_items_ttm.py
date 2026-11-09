#!/usr/bin/env python
"""
测试 search_line_items(period="ttm") 返回的数据类型
验证是否与 get_financial_metrics(period="ttm") 一致
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_financial_metrics, search_line_items

def test_ttm_line_items(ticker="AAPL", end_date="2026-07-24", limit=3):
    print(f"测试 {ticker} 的 search_line_items(period='ttm')")
    print(f"结束日期: {end_date}, 限制: {limit}\n")

    # 1. 获取 TTM 财务指标（作为基准）
    print("--- 1. get_financial_metrics(period='ttm') 基准数据 ---")
    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=limit)
    if not metrics:
        print("❌ 未获取到财务指标")
        return
    for m in metrics:
        print(f"报告期: {m.report_period}")
        print(f"  Revenue (TTM): {m.revenue:,.0f}" if m.revenue else "  Revenue: None")
        print(f"  Net Income (TTM): {m.net_income:,.0f}" if m.net_income else "  Net Income: None")
        print(f"  FCF (TTM): {m.free_cash_flow:,.0f}" if m.free_cash_flow else "  FCF: None")
        print()

    # 2. 调用 search_line_items(period="ttm")
    print("--- 2. search_line_items(period='ttm') 返回的数据 ---")
    line_items = search_line_items(
        ticker,
        line_items=[
            "free_cash_flow",
            "net_income",
            "revenue",
            "ebit",
            "working_capital",
            "total_debt",
            "cash_and_equivalents",
            "capital_expenditure",
            "depreciation_and_amortization",
        ],
        end_date=end_date,
        period="ttm",
        limit=limit,
    )
    if not line_items:
        print("❌ 未获取到行项目")
        return

    # 确保按报告期降序排列（最新在前），与 metrics 顺序一致
    sorted_items = sorted(line_items, key=lambda x: x.report_period, reverse=True)
    for i, li in enumerate(sorted_items[:limit], 1):
        print(f"记录 {i}:")
        print(f"  report_period: {li.report_period}")
        fcf = getattr(li, 'free_cash_flow', None)
        net_income = getattr(li, 'net_income', None)
        revenue = getattr(li, 'revenue', None)
        print(f"  free_cash_flow: {fcf:,.0f}" if fcf else "  free_cash_flow: None")
        print(f"  net_income: {net_income:,.0f}" if net_income else "  net_income: None")
        print(f"  revenue: {revenue:,.0f}" if revenue else "  revenue: None")
        print()

    # 3. 一致性检查（按报告期对齐）
    print("--- 3. 一致性检查 ---")
    # 取交集，确保只比较共同报告期
    metric_dict = {m.report_period: m for m in metrics}
    item_dict = {li.report_period: li for li in sorted_items}
    common_periods = sorted(set(metric_dict.keys()) & set(item_dict.keys()), reverse=True)
    if not common_periods:
        print("⚠️  无共同报告期，无法比较")
        return

    print(f"共同报告期: {common_periods}")
    all_match = True
    for period in common_periods[:limit]:
        m = metric_dict[period]
        li = item_dict[period]
        metric_fcf = getattr(m, 'free_cash_flow', None)
        item_fcf = getattr(li, 'free_cash_flow', None)
        if metric_fcf is not None and item_fcf is not None:
            if abs(metric_fcf - item_fcf) < 1e-6:
                print(f"✅ 报告期 {period}: FCF 一致 ({metric_fcf:,.0f})")
            else:
                print(f"❌ 报告期 {period}: FCF 不一致 (metric={metric_fcf:,.0f}, item={item_fcf:,.0f})")
                all_match = False
        else:
            print(f"⚠️  报告期 {period}: FCF 值缺失 (metric={metric_fcf}, item={item_fcf})")

    if all_match:
        print("✅ 所有可比较的 FCF 完全匹配，TTM 数据一致。")
    else:
        print("❌ 存在不一致，请检查数据源。")

if __name__ == "__main__":
    # 确保环境变量设置，以便走 EDGAR 路径
    os.environ["USE_EDGAR"] = "true"
    os.environ["USE_YFINANCE"] = "true"
    test_ttm_line_items("AAPL")
