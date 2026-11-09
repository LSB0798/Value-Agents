#!/usr/bin/env python
"""
正确获取 SEC EDGAR 季度数据，并打印最近 8 个季度的关键指标。
"""

import pandas as pd
from secfin import SECClient, Company

def test_secfin_quarterly_fixed(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)
    
    print(f"📊 获取 {ticker} 的季度财务数据（EDGAR）...\n")
    
    # 明确指定 period='quarterly'
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    balance_q = company.get_balance_sheet(period='quarterly').to_dataframe()
    cashflow_q = company.get_cash_flow(period='quarterly').to_dataframe()
    
    income_q.index = pd.to_datetime(income_q.index)
    balance_q.index = pd.to_datetime(balance_q.index)
    cashflow_q.index = pd.to_datetime(cashflow_q.index)
    
    income_q = income_q.sort_index()
    balance_q = balance_q.sort_index()
    cashflow_q = cashflow_q.sort_index()
    
    print(f"📅 利润表季度数: {len(income_q)}")
    print(f"📅 资产负债表季度数: {len(balance_q)}")
    print(f"📅 现金流量表季度数: {len(cashflow_q)}")
    print(f"📅 日期范围: {income_q.index.min()} 至 {income_q.index.max()}\n")
    
    # 取最近 8 个季度
    income_recent = income_q.tail(8)
    balance_recent = balance_q.tail(8)
    cashflow_recent = cashflow_q.tail(8)
    
    # 计算单季值（因为季度数据是累计值 YTD）
    # 注意：资产负债表已经是时点值，无需转换
    # 利润表和现金流量表需要差分
    income_single = income_recent.diff().fillna(income_recent)
    cashflow_single = cashflow_recent.diff().fillna(cashflow_recent)
    
    # 获取三个表的交集日期
    common_dates = income_recent.index.intersection(balance_recent.index).intersection(cashflow_recent.index)
    
    print("🔍 最近 8 个季度的关键数据（单季值）:")
    print("=" * 90)
    print(f"{'报告期':<12} {'Revenue':>18} {'Net Income':>18} {'Equity':>18} {'ROE (单季)':>12}")
    print("-" * 90)
    
    for date in common_dates:
        rev = income_single.loc[date, 'revenue'] if 'revenue' in income_single.columns else None
        ni = income_single.loc[date, 'net_income'] if 'net_income' in income_single.columns else None
        eq = balance_recent.loc[date, 'stockholders_equity'] if 'stockholders_equity' in balance_recent.columns else None
        if rev is not None and ni is not None and eq is not None and eq != 0:
            roe = ni / eq
        else:
            roe = None
        print(f"{date.strftime('%Y-%m-%d'):<12} {rev:>18,.0f} {ni:>18,.0f} {eq:>18,.0f} {roe:>12.2f}")

if __name__ == "__main__":
    test_secfin_quarterly_fixed("AAPL")
