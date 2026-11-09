#!/usr/bin/env python
"""
测试修复后的 TTM 路径是否返回合理的 ROE。
"""

import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
from valueagents.agents.src.tools.api import get_financial_metrics

def test_ttm_vs_annual(ticker="AAPL", end_date="2026-07-10"):
    print(f"测试 {ticker} 的 TTM 与年度 ROE 对比\n")
    
    # 获取 TTM 数据（最近 5 个 TTM 点）
    metrics_ttm = get_financial_metrics(ticker, end_date, period="ttm", limit=5)
    print("TTM 数据:")
    for m in metrics_ttm:
        roe = m.return_on_equity
        print(f"  {m.report_period}: ROE={roe:.2f}")
    
    # 获取年度数据（最近 5 年）
    metrics_annual = get_financial_metrics(ticker, end_date, period="annual", limit=5)
    print("\n年度数据:")
    for m in metrics_annual:
        roe = m.return_on_equity
        print(f"  {m.report_period}: ROE={roe:.2f}")

if __name__ == "__main__":
    test_ttm_vs_annual()
