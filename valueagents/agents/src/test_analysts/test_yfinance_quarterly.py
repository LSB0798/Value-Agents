#!/usr/bin/env python
"""
测试 yfinance 获取季度财务报表，并计算 TTM 值
"""

import yfinance as yf
import pandas as pd

def test_yfinance_quarterly(ticker="AAPL", quarters=40):
    """
    获取季度利润表、资产负债表、现金流量表，并展示最新4个季度的 TTM 总和。
    """
    stock = yf.Ticker(ticker)
    
    # 获取季度数据
    q_income = stock.quarterly_financials
    q_balance = stock.quarterly_balance_sheet
    q_cashflow = stock.quarterly_cashflow
    
    print(f"📊 {ticker} 季度财务数据（最近 {quarters} 个季度）")
    print("=" * 70)
    
    # 取最近 quarters 个季度
    q_income = q_income.iloc[:, :quarters]
    q_balance = q_balance.iloc[:, :quarters]
    q_cashflow = q_cashflow.iloc[:, :quarters]
    
    # 显示列名（即报告期）
    print(f"\n📅 报告期: {q_income.columns.tolist()}")
    
    # 打印利润表关键项
    print("\n📈 利润表 (关键项):")
    income_rows = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income', 'EBIT', 'EBITDA']
    for row in income_rows:
        if row in q_income.index:
            print(f"  {row}:\n{q_income.loc[row]}")
    
    # 打印资产负债表关键项
    print("\n📋 资产负债表 (关键项):")
    balance_rows = ['Total Assets', 'Total Liabilities', 'Stockholders Equity', 'Total Debt', 'Cash']
    for row in balance_rows:
        if row in q_balance.index:
            print(f"  {row}:\n{q_balance.loc[row]}")
    
    # 打印现金流量表关键项
    print("\n💵 现金流量表 (关键项):")
    cashflow_rows = ['Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow']
    for row in cashflow_rows:
        if row in q_cashflow.index:
            print(f"  {row}:\n{q_cashflow.loc[row]}")
    
    # 计算 TTM（最近4个季度总和）
    print("\n🔄 TTM 值（最近4个季度总和）:")
    ttm_income = q_income.iloc[:, :4].sum(axis=1)
    ttm_balance = q_balance.iloc[:, :4].sum(axis=1)
    ttm_cashflow = q_cashflow.iloc[:, :4].sum(axis=1)
    
    # 提取关键 TTM 指标
    print(f"  Total Revenue (TTM): {ttm_income.get('Total Revenue', 'N/A')}")
    print(f"  Net Income (TTM): {ttm_income.get('Net Income', 'N/A')}")
    print(f"  EBIT (TTM): {ttm_income.get('EBIT', 'N/A')}")
    print(f"  EBITDA (TTM): {ttm_income.get('EBITDA', 'N/A')}")
    print(f"  Free Cash Flow (TTM): {ttm_cashflow.get('Free Cash Flow', 'N/A')}")
    print(f"  Total Debt (latest): {q_balance.loc['Total Debt'].iloc[0] if 'Total Debt' in q_balance.index else 'N/A'}")
    print(f"  Stockholders Equity (latest): {q_balance.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in q_balance.index else 'N/A'}")
    
    # 计算 ROE (TTM Net Income / 最新权益)
    ni_ttm = ttm_income.get('Net Income')
    equity = q_balance.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in q_balance.index else None
    if ni_ttm is not None and equity is not None and equity != 0:
        roe_ttm = ni_ttm / equity
        print(f"  ROE (TTM): {roe_ttm:.2f} ({roe_ttm*100:.1f}%)")
    
    return q_income, q_balance, q_cashflow

if __name__ == "__main__":
    test_yfinance_quarterly("AAPL", quarters=8)
