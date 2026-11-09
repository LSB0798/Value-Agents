#!/usr/bin/env python
"""
测试分红数据在数据流中的传递情况
验证 secfin → api.py → ben_graham_agent 的链路
"""

import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import pandas as pd
from valueagents.agents.src.tools.api import (
    search_line_items,
    get_financial_metrics,
    get_sec_client,
    Company,
)

TICKER = "AAPL"
END_DATE = "2026-07-10"

def test_secfin_dividend():
    """直接从 secfin 获取原始数据"""
    print("="*60)
    print("1. 从 secfin 获取原始 dividends_paid")
    print("="*60)
    
    client = get_sec_client()
    company = Company(TICKER, client)
    
    # 获取现金流表 DataFrame
    cashflow_df = company.get_cash_flow().to_dataframe()
    cashflow_df.index = pd.to_datetime(cashflow_df.index)
    annual_cashflow = cashflow_df.groupby(cashflow_df.index.year).last()
    
    print(f"Cashflow columns: {annual_cashflow.columns.tolist()}")
    print("\n最近 5 年的 dividends_paid:")
    years = sorted(annual_cashflow.index, reverse=True)[:5]
    for yr in years:
        val = annual_cashflow.loc[yr, 'dividends_paid'] if 'dividends_paid' in annual_cashflow.columns else None
        print(f"  {yr}: {val}")

def test_search_line_items_dividend():
    """通过 search_line_items 获取 LineItem 中的分红数据"""
    print("\n" + "="*60)
    print("2. 通过 search_line_items 获取 LineItem 中的分红数据")
    print("="*60)
    
    line_items_needed = ['dividends_and_other_cash_distributions', 'net_income', 'outstanding_shares']
    items = search_line_items(TICKER, line_items_needed, END_DATE, period="annual", limit=5)
    
    print(f"LineItem 记录数: {len(items)}")
    for i, item in enumerate(items):
        div = item.dividends_and_other_cash_distributions
        print(f"  {i+1}. {item.report_period}: dividends_and_other_cash_distributions = {div}")

def test_ben_graham_dividend():
    """运行 ben_graham_agent 查看 reasoning 中的分红信息"""
    print("\n" + "="*60)
    print("3. Ben Graham Agent 的输出")
    print("="*60)
    
    from valueagents.agents.src.analysts.ben_graham import ben_graham_agent
    
    state = {
        "data": {
            "tickers": [TICKER],
            "end_date": END_DATE,
            "start_date": "2025-07-10",
            "analyst_signals": {},
        },
        "metadata": {
            "show_reasoning": True,
        }
    }
    
    result = ben_graham_agent(state, agent_id="ben_graham_agent")
    
    # 获取信号
    signals = state["data"]["analyst_signals"].get("ben_graham_agent", {})
    for ticker, sig in signals.items():
        print(f"\nSignal: {sig.get('signal')}")
        print(f"Confidence: {sig.get('confidence')}")
        print(f"Reasoning:\n{sig.get('reasoning')}")

if __name__ == "__main__":
    test_secfin_dividend()
    test_search_line_items_dividend()
    test_ben_graham_dividend()
