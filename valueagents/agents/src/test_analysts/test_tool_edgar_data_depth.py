#!/usr/bin/env python
"""
测试 secfin 能够获取的历史数据深度，并对比 yfinance 的数据量。
"""

import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import pandas as pd
from valueagents.agents.src.tools.api import get_sec_client, get_financial_metrics
import yfinance as yf

def test_secfin_depth(ticker="AAPL"):
    """直接使用 secfin 获取年度和季度数据，查看数据行数及年份范围"""
    client = get_sec_client()
    from secfin import Company
    company = Company(ticker, client)

    print(f"🔍 测试 secfin 的数据深度: {ticker}")
    print("=" * 60)

    # 1. 年度利润表
    income_annual = company.get_income_statement().to_dataframe()
    print(f"年度利润表 shape: {income_annual.shape}")
    print(f"年度利润表索引类型: {income_annual.index.dtype}")
    if len(income_annual) > 0:
        years = sorted(income_annual.index)
        print(f"年份范围: {years[0]} 至 {years[-1]} (共 {len(years)} 年)")
        print("最近5年:")
        print(income_annual.tail(5)[['revenue', 'net_income']])
    print()

    # 2. 年度资产负债表
    balance_annual = company.get_balance_sheet().to_dataframe()
    print(f"年度资产负债表 shape: {balance_annual.shape}")
    if len(balance_annual) > 0:
        years = sorted(balance_annual.index)
        print(f"年份范围: {years[0]} 至 {years[-1]} (共 {len(years)} 年)")
    print()

    # 3. 季度利润表（如果可用）
    try:
        income_quarterly = company.get_income_statement().to_dataframe(period="quarterly")
        print(f"季度利润表 shape: {income_quarterly.shape}")
        if len(income_quarterly) > 0:
            dates = sorted(income_quarterly.index)
            print(f"季度范围: {dates[0]} 至 {dates[-1]} (共 {len(dates)} 个季度)")
            print("最近4个季度:")
            print(income_quarterly.tail(4)[['revenue', 'net_income']])
    except Exception as e:
        print(f"获取季度数据失败: {e}")
    print()

def test_yfinance_depth(ticker="AAPL"):
    """测试 yfinance 能获取多少年度和季度数据"""
    print(f"🔍 测试 yfinance 的数据深度: {ticker}")
    print("=" * 60)
    stock = yf.Ticker(ticker)

    # 年度财务数据
    fin_annual = stock.financials
    print(f"年度利润表 shape: {fin_annual.shape}")
    if not fin_annual.empty:
        years = sorted(fin_annual.columns)
        print(f"年度年份范围: {years[0]} 至 {years[-1]} (共 {len(years)} 年)")
        print("最近5年:")
        print(fin_annual.iloc[:, :5].loc[['Total Revenue', 'Net Income']].T)  # 转置以便阅读

    # 季度财务数据
    fin_quarterly = stock.quarterly_financials
    print(f"\n季度利润表 shape: {fin_quarterly.shape}")
    if not fin_quarterly.empty:
        dates = sorted(fin_quarterly.columns)
        print(f"季度范围: {dates[0]} 至 {dates[-1]} (共 {len(dates)} 个季度)")
        print("最近4个季度:")
        print(fin_quarterly.iloc[:, :4].loc[['Total Revenue', 'Net Income']].T)

def test_get_financial_metrics_limit():
    """测试通过 get_financial_metrics 能否通过 limit 参数获取更多数据"""
    print("\n🔍 测试 get_financial_metrics 的 limit 参数")
    print("=" * 60)
    for limit in [5, 10, 20]:
        metrics = get_financial_metrics("AAPL", "2026-07-10", period="annual", limit=limit)
        print(f"limit={limit} -> 返回 {len(metrics)} 条记录")
        if metrics:
            years = [m.report_period[:4] for m in metrics]
            print(f"  年份: {sorted(years)}")
    print()

if __name__ == "__main__":
    test_secfin_depth()
    test_yfinance_depth()
    test_get_financial_metrics_limit()
