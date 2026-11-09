#!/usr/bin/env python
"""
获取 SEC EDGAR 季度数据，并打印所有季度的关键指标（含 NaN 处理）。
"""

import pandas as pd
from secfin import SECClient, Company

def test_secfin_quarterly_all(ticker="AAPL", limit=None):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)
    
    print(f"📊 获取 {ticker} 的季度财务数据（EDGAR）...\n")
    
    # 获取季度数据
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
    
    # 计算单季值（利润表和现金流量表是累计值，需差分）
    income_single = income_q.diff().fillna(income_q)
    cashflow_single = cashflow_q.diff().fillna(cashflow_q)
    
    # 合并所有日期（并集）
    all_dates = income_single.index.union(balance_q.index).union(cashflow_single.index)
    all_dates = pd.DatetimeIndex(all_dates).sort_values()
    
    if limit is not None and limit > 0:
        all_dates = all_dates[-limit:]
    
    # 准备数据
    rev_series = income_single['revenue'] if 'revenue' in income_single.columns else pd.Series(index=income_single.index)
    ni_series = income_single['net_income'] if 'net_income' in income_single.columns else pd.Series(index=income_single.index)
    eq_series = balance_q['stockholders_equity'] if 'stockholders_equity' in balance_q.columns else pd.Series(index=balance_q.index)
    fcf_series = cashflow_single['free_cash_flow'] if 'free_cash_flow' in cashflow_single.columns else pd.Series(index=cashflow_single.index)
    
    # 对齐到 all_dates
    rev_aligned = rev_series.reindex(all_dates)
    ni_aligned = ni_series.reindex(all_dates)
    eq_aligned = eq_series.reindex(all_dates)
    fcf_aligned = fcf_series.reindex(all_dates)
    
    print("🔍 所有季度的关键数据（单季值）:")
    print("=" * 110)
    print(f"{'报告期':<12} {'Revenue':>18} {'Net Income':>18} {'Equity':>18} {'ROE (单季)':>12} {'FCF':>18}")
    print("-" * 110)
    
    for date in all_dates:
        rev = rev_aligned.loc[date]
        ni = ni_aligned.loc[date]
        eq = eq_aligned.loc[date]
        fcf = fcf_aligned.loc[date]
        
        # 处理 NaN/None，转换为空字符串
        rev_str = f"{rev:>18,.0f}" if pd.notna(rev) else " " * 18
        ni_str = f"{ni:>18,.0f}" if pd.notna(ni) else " " * 18
        eq_str = f"{eq:>18,.0f}" if pd.notna(eq) else " " * 18
        fcf_str = f"{fcf:>18,.0f}" if pd.notna(fcf) else " " * 18
        
        # 计算单季 ROE
        if pd.notna(ni) and pd.notna(eq) and eq != 0:
            roe_val = ni / eq
        else:
            roe_val = None
        roe_str = f"{roe_val:>12.2f}" if pd.notna(roe_val) else " " * 12
        
        print(f"{date.strftime('%Y-%m-%d'):<12} {rev_str} {ni_str} {eq_str} {roe_str} {fcf_str}")

if __name__ == "__main__":
    # 打印所有季度（不限制）
    test_secfin_quarterly_all("AAPL", limit=None)
    # 如果想只打印最近 20 个季度，可改为 limit=20
