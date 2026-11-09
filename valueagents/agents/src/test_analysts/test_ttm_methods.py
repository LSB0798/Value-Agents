#!/usr/bin/env python
"""
测试多种 TTM 计算方法，比较其与年度数据的一致性。
"""

import pandas as pd
import sys

# 1. 测试 secfin
try:
    from secfin import SECClient, Company
    SECFIN_AVAILABLE = True
except ImportError:
    SECFIN_AVAILABLE = False

# 2. 测试 edgartools
try:
    from edgar import Company as EdgarCompany
    from edgar.enums import PeriodType
    EDGARTOOLS_AVAILABLE = True
except ImportError:
    EDGARTOOLS_AVAILABLE = False

def test_secfin_ttm(ticker="AAPL"):
    print("\n" + "="*60)
    print("测试 secfin 内置 TTM 方法")
    print("="*60)
    if not SECFIN_AVAILABLE:
        print("secfin 未安装，跳过")
        return
    
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)
    
    # 获取 income statement 对象
    income = company.get_income_statement()
    balance = company.get_balance_sheet()
    cashflow = company.get_cash_flow()
    
    # 使用内置 ttm 方法（如果有）
    # 注意：secfin 的 ttm() 方法存在于某些版本，但可能不是所有字段都支持
    try:
        ttm_rev = income.revenue.ttm()
        ttm_ni = income.net_income.ttm()
        # 注意：ttm 返回的是 Series 还是数值？可能需要处理
        print(f"TTM 收入: {ttm_rev}")
        print(f"TTM 净收入: {ttm_ni}")
    except AttributeError as e:
        print(f"secfin 不支持 ttm() 方法: {e}")
        # 降级：使用 to_dataframe 手动计算
        print("降级到手动计算...")
        income_df = income.to_dataframe()
        # 获取最近四个季度的数据（假设索引为日期，需要按升序）
        income_df = income_df.sort_index()
        # 取最近 4 个季度（假设数据为累计值）
        # 但无法确定累计性质，放弃
        print("无法确定季度数据是否为累计值，跳过")
    
    # 使用 growth() 和 cagr() 等方法检查
    try:
        rev_growth = income.revenue.growth()
        rev_cagr = income.revenue.cagr(years=5)
        print(f"收入同比增长率: {rev_growth}")
        print(f"收入 5 年 CAGR: {rev_cagr}")
    except AttributeError:
        pass

def test_edgartools_ttm(ticker="AAPL"):
    print("\n" + "="*60)
    print("测试 edgartools 的 TTM 功能")
    print("="*60)
    if not EDGARTOOLS_AVAILABLE:
        print("edgartools 未安装，跳过")
        return
    
    try:
        company = EdgarCompany(ticker)
        # 获取季度数据
        quarterly = company.income_statement(periods=8, annual=False)
        print("最近 8 个季度的收入:")
        print(quarterly.data[['revenue']].tail(8))
        
        # 获取 TTM 数据
        ttm = company.income_statement(period_type=PeriodType.TTM)
        print("\nTTM 收入数据:")
        print(ttm.data[['revenue']].tail(3))
    except Exception as e:
        print(f"edgartools 测试失败: {e}")

def test_manual_ttm(ticker="AAPL"):
    print("\n" + "="*60)
    print("手动差分 + 滚动求和（参考）")
    print("="*60)
    if not SECFIN_AVAILABLE:
        print("secfin 未安装，无法手动获取数据")
        return
    
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)
    
    # 获取季度数据
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    balance_q = company.get_balance_sheet(period='quarterly').to_dataframe()
    
    income_q.index = pd.to_datetime(income_q.index)
    balance_q.index = pd.to_datetime(balance_q.index)
    
    income_q = income_q.sort_index()
    balance_q = balance_q.sort_index()
    
    # 转换为单季值（差分）
    income_single = income_q.diff().fillna(income_q)
    
    # 取最近 8 个季度，计算滚动 TTM
    income_single_recent = income_single.tail(8)
    equity_recent = balance_q.tail(8)
    
    # 对齐日期（取交集）
    common_dates = income_single_recent.index.intersection(equity_recent.index)
    income_single_recent = income_single_recent.loc[common_dates]
    equity_recent = equity_recent.loc[common_dates]
    
    # 滚动 TTM（4 个季度）
    ttm_ni = []
    ttm_dates = []
    for i in range(3, len(income_single_recent)):
        ni_sum = income_single_recent.iloc[i-3:i+1]['net_income'].sum()
        ttm_ni.append(ni_sum)
        ttm_dates.append(income_single_recent.index[i])
    
    print("最近几个 TTM 净收入:")
    for dt, ni in zip(ttm_dates[-5:], ttm_ni[-5:]):
        print(f"  {dt.strftime('%Y-%m-%d')}: {ni:,.0f}")

if __name__ == "__main__":
    test_secfin_ttm("AAPL")
    test_edgartools_ttm("AAPL")
    test_manual_ttm("AAPL")
    print("\n建议：优先使用 yfinance 获取 TTM 数据，因为它可靠且简单。")
