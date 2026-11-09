#!/usr/bin/env python
"""
扩展补全所有字段的 Q4 单季值（不计算 TTM）。
"""

import pandas as pd
from secfin import SECClient, Company

def test_secfin_quarterly_complete_single(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)

    # 获取季度数据（累计值）
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    balance_q = company.get_balance_sheet(period='quarterly').to_dataframe()
    cashflow_q = company.get_cash_flow(period='quarterly').to_dataframe()

    income_q.index = pd.to_datetime(income_q.index)
    balance_q.index = pd.to_datetime(balance_q.index)
    cashflow_q.index = pd.to_datetime(cashflow_q.index)

    income_q = income_q.sort_index()
    balance_q = balance_q.sort_index()
    cashflow_q = cashflow_q.sort_index()

    # 获取年度数据（用于补全 Q4）
    income_a = company.get_income_statement(period='annual').to_dataframe()
    cashflow_a = company.get_cash_flow(period='annual').to_dataframe()
    income_a.index = pd.to_datetime(income_a.index)
    cashflow_a.index = pd.to_datetime(cashflow_a.index)
    income_a = income_a.sort_index()
    cashflow_a = cashflow_a.sort_index()

    # 对齐三个季度表（取交集）
    common_idx = income_q.index.intersection(balance_q.index).intersection(cashflow_q.index)
    income_q = income_q.loc[common_idx]
    balance_q = balance_q.loc[common_idx]
    cashflow_q = cashflow_q.loc[common_idx]

    # 差分得到单季值（不含 Q4）
    income_single = income_q.diff().fillna(income_q)
    cashflow_single = cashflow_q.diff().fillna(cashflow_q)

    # 定义需要补全的利润表字段
    profit_columns = ['revenue', 'net_income', 'operating_income', 'interest_expense', 'gross_profit']
    # 补全利润表字段的 Q4 单季值
    for col in profit_columns:
        if col not in income_single.columns:
            continue
        for a_date in income_a.index:
            if a_date in income_single.index and pd.notna(income_single.loc[a_date, col]):
                continue
            q_dates = income_q.index[income_q.index < a_date]
            if len(q_dates) == 0:
                continue
            q3_date = q_dates[-1]
            if q3_date.year != a_date.year:
                continue
            q3_val = income_q.loc[q3_date, col] if col in income_q.columns else None
            annual_val = income_a.loc[a_date, col] if col in income_a.columns else None
            if q3_val is not None and annual_val is not None and pd.notna(q3_val) and pd.notna(annual_val):
                income_single.loc[a_date, col] = annual_val - q3_val
                # 可选打印调试
                # print(f"补全 {col} for {a_date}: {annual_val - q3_val}")

    # 补全现金流量表 free_cash_flow 的 Q4
    if 'free_cash_flow' in cashflow_single.columns:
        for a_date in cashflow_a.index:
            if a_date in cashflow_single.index and pd.notna(cashflow_single.loc[a_date, 'free_cash_flow']):
                continue
            q_dates = cashflow_q.index[cashflow_q.index < a_date]
            if len(q_dates) == 0:
                continue
            q3_date = q_dates[-1]
            if q3_date.year != a_date.year:
                continue
            q3_val = cashflow_q.loc[q3_date, 'free_cash_flow'] if 'free_cash_flow' in cashflow_q.columns else None
            annual_val = cashflow_a.loc[a_date, 'free_cash_flow'] if 'free_cash_flow' in cashflow_a.columns else None
            if q3_val is not None and annual_val is not None and pd.notna(q3_val) and pd.notna(annual_val):
                cashflow_single.loc[a_date, 'free_cash_flow'] = annual_val - q3_val

    # 排序
    income_single = income_single.sort_index()
    cashflow_single = cashflow_single.sort_index()

    # 将资产负债表对齐到利润表日期（前向填充）
    balance_aligned = balance_q.reindex(income_single.index, method='ffill')

    # 提取所有需要的字段（单季值）
    # 利润表
    rev = income_single['revenue']
    ni = income_single['net_income']
    ebit = income_single['operating_income'] if 'operating_income' in income_single.columns else pd.Series(index=income_single.index)
    interest = income_single['interest_expense'] if 'interest_expense' in income_single.columns else pd.Series(index=income_single.index)
    gross_profit = income_single['gross_profit'] if 'gross_profit' in income_single.columns else pd.Series(index=income_single.index)
    shares_outstanding = income_single['shares_outstanding'] if 'shares_outstanding' in income_single.columns else pd.Series(index=income_single.index)

    # 现金流量表
    fcf = cashflow_single['free_cash_flow'] if 'free_cash_flow' in cashflow_single.columns else pd.Series(index=cashflow_single.index)

    # 资产负债表（时点值）
    equity = balance_aligned['stockholders_equity']
    total_debt = balance_aligned['long_term_debt']
    cash = balance_aligned['cash']
    current_assets = balance_aligned['current_assets']
    current_liabilities = balance_aligned['current_liabilities']

    # 合并成 DataFrame
    df_single = pd.DataFrame({
        'revenue': rev,
        'net_income': ni,
        'ebit': ebit,
        'interest_expense': interest,
        'gross_profit': gross_profit,
        'free_cash_flow': fcf,
        'equity': equity,
        'total_debt': total_debt,
        'cash': cash,
        'current_assets': current_assets,
        'current_liabilities': current_liabilities,
        'shares_outstanding': shares_outstanding
    }, index=income_single.index)

    # 打印最近 8 个季度的单季值（补全后）
    print("\n补全后的单季值（最近 8 个季度）:")
    print("=" * 160)
    print(f"{'报告期':<12} {'Revenue':>18} {'Net Income':>18} {'EBIT':>18} {'FCF':>18} {'Equity':>18}")
    print("-" * 160)
    for date in df_single.index[-8:]:
        rev = df_single.loc[date, 'revenue']
        ni = df_single.loc[date, 'net_income']
        ebit = df_single.loc[date, 'ebit']
        fcf = df_single.loc[date, 'free_cash_flow']
        eq = df_single.loc[date, 'equity']
        print(f"{date.strftime('%Y-%m-%d'):<12} {rev:>18,.0f} {ni:>18,.0f} {ebit:>18,.0f} {fcf:>18,.0f} {eq:>18,.0f}")

    # 验证 2025-09-27 的补全值
    if '2025-09-27' in df_single.index:
        val_ni = df_single.loc['2025-09-27', 'net_income']
        val_rev = df_single.loc['2025-09-27', 'revenue']
        expected_ni = 27_466_000_000
        expected_rev = 102_466_000_000  # 416.161B - 313.695B
        print(f"\n2025-09-27 补全值:")
        print(f"  Revenue: {val_rev:,.0f} (期望 {expected_rev:,})")
        print(f"  Net Income: {val_ni:,.0f} (期望 {expected_ni:,})")
        if abs(val_ni - expected_ni) < 1 and abs(val_rev - expected_rev) < 1:
            print("✅ 补全正确！")
        else:
            print(f"❌ 补全差异: Net Income: {val_ni - expected_ni:,.0f}, Revenue: {val_rev - expected_rev:,.0f}")

if __name__ == "__main__":
    test_secfin_quarterly_complete_single("AAPL")
