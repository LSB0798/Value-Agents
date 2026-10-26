#!/usr/bin/env python
"""
诊断 _get_financial_metrics_edgar_ttm 的 ROE 异常问题
"""

import pandas as pd
from secfin import SECClient, Company

def diagnose_ttm_roe(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)
    
    # 获取季度数据（必须指定 period='quarterly'）
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    balance_q = company.get_balance_sheet(period='quarterly').to_dataframe()
    cashflow_q = company.get_cash_flow(period='quarterly').to_dataframe()
    
    # 获取年度数据用于对比
    income_a = company.get_income_statement(period='annual').to_dataframe()
    balance_a = company.get_balance_sheet(period='annual').to_dataframe()
    
    # 索引转 datetime
    income_q.index = pd.to_datetime(income_q.index)
    balance_q.index = pd.to_datetime(balance_q.index)
    cashflow_q.index = pd.to_datetime(cashflow_q.index)
    income_a.index = pd.to_datetime(income_a.index)
    balance_a.index = pd.to_datetime(balance_a.index)
    
    # 排序
    income_q = income_q.sort_index()
    balance_q = balance_q.sort_index()
    cashflow_q = cashflow_q.sort_index()
    income_a = income_a.sort_index()
    balance_a = balance_a.sort_index()
    
    # 对齐三个季度表（交集）
    common_dates = income_q.index.intersection(balance_q.index).intersection(cashflow_q.index)
    income_q = income_q.loc[common_dates]
    balance_q = balance_q.loc[common_dates]
    cashflow_q = cashflow_q.loc[common_dates]
    
    # 转换为单季值（累计值差分）
    income_single = income_q.diff().fillna(income_q)
    cashflow_single = cashflow_q.diff().fillna(cashflow_q)
    
    # 准备存储 TTM 序列
    ttm_dates = []
    ttm_ni = []
    ttm_equity = []
    
    # 滚动窗口：至少需要 4 个季度
    for i in range(3, len(income_q)):
        idx_range = income_q.index[i-3:i+1]  # 最近四个季度
        # 取单季净收入之和
        ni_sum = income_single.loc[idx_range, 'net_income'].sum()
        # 取该季度末权益
        eq = balance_q.loc[idx_range[-1], 'stockholders_equity']
        ttm_dates.append(idx_range[-1])
        ttm_ni.append(ni_sum)
        ttm_equity.append(eq)
    
    # 转为 DataFrame
    ttm_df = pd.DataFrame({'date': ttm_dates, 'ttm_ni': ttm_ni, 'equity': ttm_equity})
    ttm_df['roe'] = ttm_df['ttm_ni'] / ttm_df['equity']
    
    # 打印最近几个季度（例如最近 8 个）
    print("TTM 诊断结果（最近 8 个 TTM 点）:")
    print("=" * 80)
    print(f"{'报告期':<12} {'TTM净收入':>18} {'权益':>18} {'ROE':>12}")
    print("-" * 80)
    for _, row in ttm_df.tail(8).iterrows():
        print(f"{row['date'].strftime('%Y-%m-%d'):<12} {row['ttm_ni']:>18,.0f} {row['equity']:>18,.0f} {row['roe']:>12.2f}")
    
    # 对比年度数据（最近 5 年）
    print("\n年度数据对比（最近 5 年）:")
    print("=" * 80)
    print(f"{'财年':<8} {'年度净收入':>18} {'年末权益':>18} {'年度ROE':>12}")
    print("-" * 80)
    for yr in range(2021, 2026):
        if yr in income_a.index.year:
            idx = income_a[income_a.index.year == yr].index[-1]
            ni = income_a.loc[idx, 'net_income']
            eq = balance_a.loc[idx, 'stockholders_equity']
            roe = ni / eq
            print(f"{yr:<8} {ni:>18,.0f} {eq:>18,.0f} {roe:>12.2f}")
    
    # 关键检查：看看最近 TTM 净收入是否与年度净收入接近
    if len(ttm_df) > 0:
        latest_ttm = ttm_df.iloc[-1]
        latest_year = income_a.index[-1].year
        latest_annual_ni = income_a.loc[income_a.index[-1], 'net_income']
        print(f"\n最新 TTM 净收入: {latest_ttm['ttm_ni']:,.0f}")
        print(f"最近年度净收入 ({latest_year}): {latest_annual_ni:,.0f}")
        print(f"差异: {latest_ttm['ttm_ni'] - latest_annual_ni:,.0f}")
        print(f"TTM ROE: {latest_ttm['roe']:.2f}")
        print(f"年度 ROE: {latest_annual_ni / balance_a.loc[income_a.index[-1], 'stockholders_equity']:.2f}")

if __name__ == "__main__":
    diagnose_ttm_roe("AAPL")
