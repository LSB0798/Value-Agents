#!/usr/bin/env python
"""
独立测试 EDGAR 数据获取功能，验证关键字段是否填充。
"""

import os
# 必须在导入任何 valueagents 模块之前设置环境变量
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import json
import pandas as pd

# 导入 api 中的函数
from valueagents.agents.src.tools.api import (
    get_financial_metrics,
    search_line_items,
    get_market_cap,
)

TICKER = "AAPL"
END_DATE = "2026-07-10"

def test_financial_metrics():
    print("\n=== Testing get_financial_metrics (EDGAR) ===")
    metrics = get_financial_metrics(TICKER, END_DATE, period="ttm", limit=5)
    print(f"Number of metrics: {len(metrics)}")
    if metrics:
        first = metrics[0]
        print("First metric fields (non-None only):")
        for field, value in first.model_dump().items():
            if value is not None:
                print(f"  {field}: {value}")
        # 检查关键字段（注意 FinancialMetrics 没有 free_cash_flow，只有 free_cash_flow_yield）
        print(f"\nKey fields for DCF (from metrics):")
        print(f"  market_cap: {first.market_cap}")
        print(f"  price_to_earnings_ratio: {first.price_to_earnings_ratio}")
        print(f"  return_on_equity: {first.return_on_equity}")
        # free_cash_flow 应从 LineItem 获取
    else:
        print("No metrics returned.")

def test_search_line_items():
    print("\n=== Testing search_line_items (EDGAR) ===")
    line_items_needed = ['free_cash_flow', 'ebit', 'interest_expense', 
                         'capital_expenditure', 'net_income', 'total_debt', 'outstanding_shares']
    items = search_line_items(TICKER, line_items_needed, END_DATE, period="ttm", limit=10)
    print(f"Number of line items: {len(items)}")
    if items:
        first = items[0]
        print("LineItem fields (non-None only):")
        for field, value in first.model_dump().items():
            if value is not None:
                print(f"  {field}: {value}")
        # 检查关键字段
        print(f"\nKey fields for DCF (from LineItem):")
        print(f"  free_cash_flow: {first.free_cash_flow}")
        print(f"  outstanding_shares: {first.outstanding_shares}")
        print(f"  net_income: {first.net_income}")
        print(f"  ebit: {first.ebit}")
        print(f"  interest_expense: {first.interest_expense}")
        print(f"  capital_expenditure: {first.capital_expenditure}")
        print(f"  total_debt: {first.total_debt}")
    else:
        print("No line items returned.")

def test_market_cap():
    print("\n=== Testing get_market_cap (EDGAR mode) ===")
    market_cap = get_market_cap(TICKER, END_DATE)
    print(f"Market cap: {market_cap}")

if __name__ == "__main__":
    print(f"Testing EDGAR data for {TICKER} with end_date={END_DATE}")
    test_financial_metrics()
    test_search_line_items()
    test_market_cap()
    print("\nAll tests completed.")