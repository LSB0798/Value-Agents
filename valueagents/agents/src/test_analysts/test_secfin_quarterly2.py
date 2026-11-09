#!/usr/bin/env python
"""
获取 EDGAR 季度数据，以利润表日期为主，对齐资产负债表和现金流量表。
"""

import pandas as pd
from secfin import SECClient, Company

def test_secfin_quarterly(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)

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

    # 以利润表日期为主，将其他表对齐到利润表日期
    # 使用 reindex 并用前向填充 (ffill) 补充缺失值
    common_index = income_q.index
    balance_aligned = balance_q.reindex(common_index, method='ffill')
    cashflow_aligned = cashflow_q.reindex(common_index, method='ffill')

    # 取最近 8 个季度
    income_recent = income_q.tail(8)
    balance_recent = balance_aligned.tail(8)
    cashflow_recent = cashflow_aligned.tail(8)

    # 计算单季值（利润表是累计值，需要差分）
    income_single = income_recent.diff().fillna(income_recent)
    cashflow_single = cashflow_recent.diff().fillna(cashflow_recent)

    print("🔍 最近 8 个季度的关键数据（单季值）:")
    print("=" * 90)
    print(f"{'报告期':<12} {'Revenue':>18} {'Net Income':>18} {'Equity':>18} {'ROE (单季)':>12}")
    print("-" * 90)

    for date in income_recent.index:
        rev = income_single.loc[date, 'revenue'] if 'revenue' in income_single.columns else None
        ni = income_single.loc[date, 'net_income'] if 'net_income' in income_single.columns else None
        eq = balance_recent.loc[date, 'stockholders_equity'] if 'stockholders_equity' in balance_recent.columns else None
        if rev is not None and ni is not None and eq is not None and eq != 0:
            roe = ni / eq
        else:
            roe = None
        print(f"{date.strftime('%Y-%m-%d'):<12} {rev:>18,.0f} {ni:>18,.0f} {eq:>18,.0f} {roe:>12.2f}")

if __name__ == "__main__":
    test_secfin_quarterly("AAPL")
