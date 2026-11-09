#!/usr/bin/env python
"""
测试 _get_financial_metrics_roic_ttm 是否正确返回 TTM 合成数据
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_financial_metrics

def test_ttm_synthesis(ticker="AAPL", end_date="2026-07-24", limit=3):
    print(f"测试 {ticker} 的 TTM 数据合成")
    print(f"结束日期: {end_date}, 限制: {limit} 条")
    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=limit)
    if not metrics:
        print("❌ 未获取到任何数据")
        return
    print(f"✅ 获取到 {len(metrics)} 条 TTM 记录\n")
    for idx, m in enumerate(metrics, 1):
        print(f"--- 记录 {idx} ---")
        print(f"报告期: {m.report_period}")
        print(f"  Revenue (TTM): {m.revenue:,.0f}" if m.revenue else "  Revenue: None")
        print(f"  Net Income (TTM): {m.net_income:,.0f}" if m.net_income else "  Net Income: None")
        print(f"  EBIT (TTM): {m.ebit:,.0f}" if m.ebit else "  EBIT: None")
        print(f"  FCF (TTM): {m.free_cash_flow:,.0f}" if m.free_cash_flow else "  FCF: None")
        print(f"  EBITDA (TTM): {m.ebitda:,.0f}" if hasattr(m, 'ebitda') and m.ebitda else "  EBITDA: None")
        print(f"  ROE (TTM): {m.return_on_equity:.2%}" if m.return_on_equity else "  ROE: None")
        print(f"  ROIC (TTM): {m.return_on_invested_capital:.2%}" if m.return_on_invested_capital else "  ROIC: None")
        print()

if __name__ == "__main__":
    # 设置环境变量，确保走 ROIC 路径
    os.environ["USE_EDGAR"] = "true"
    test_ttm_synthesis("AAPL")
