#!/usr/bin/env python
"""
专门测试利润表 Q4 补全逻辑，打印详细中间步骤。
"""

import pandas as pd
from secfin import SECClient, Company

def test_secfin_quarterly_fix(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)

    # 获取季度数据（累计值）
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    income_q.index = pd.to_datetime(income_q.index)
    income_q = income_q.sort_index()

    # 获取年度数据（全年总和）
    income_a = company.get_income_statement(period='annual').to_dataframe()
    income_a.index = pd.to_datetime(income_a.index)
    income_a = income_a.sort_index()

    print("年度数据索引（最近 5 年）:")
    print(income_a.index[-5:])

    # 计算单季值（差分累计值）
    income_single = income_q.diff().fillna(income_q)

    print("\n补全 Q4 前的单季值（最近 8 个季度）:")
    print(income_single[['revenue', 'net_income']].tail(8))

    # 补全 Q4 单季值
    for a_date in income_a.index:
        fiscal_year = a_date.year
        print(f"\n处理财年 {fiscal_year}，日期 {a_date.strftime('%Y-%m-%d')}")

        # 寻找该财年的最后一个季报日期（Q3）
        q_dates = income_q.index[income_q.index < a_date]
        if len(q_dates) == 0:
            print("  没有早于该日期的季报，跳过")
            continue
        q3_date = q_dates[-1]
        if q3_date.year != fiscal_year:
            print(f"  最后一个季报日期 {q3_date.strftime('%Y-%m-%d')} 不属于该财年，跳过")
            continue

        print(f"  最后一个季报日期 (Q3): {q3_date.strftime('%Y-%m-%d')}")

        # 获取 Q3 累计值
        q3_row = income_q.loc[q3_date]
        if q3_row[['revenue', 'net_income']].isna().any():
            print("  Q3 累计值有 NaN，跳过")
            continue

        # 获取年度值
        annual_row = income_a.loc[a_date]
        if annual_row[['revenue', 'net_income']].isna().any():
            print("  年度值有 NaN，跳过")
            continue

        q4_revenue = annual_row['revenue'] - q3_row['revenue']
        q4_net_income = annual_row['net_income'] - q3_row['net_income']
        print(f"  推算 Q4: Revenue={q4_revenue:,.0f}, Net Income={q4_net_income:,.0f}")

        # 插入到 income_single
        income_single.loc[a_date, 'revenue'] = q4_revenue
        income_single.loc[a_date, 'net_income'] = q4_net_income
        print(f"  已将 Q4 插入到 {a_date.strftime('%Y-%m-%d')}")

    print("\n补全 Q4 后的单季值（最近 8 个季度）:")
    print(income_single[['revenue', 'net_income']].tail(8))

    # 验证 2025-09-27 的 TTM
    if '2025-09-27' in income_single.index:
        # 计算 2025-09-27 的 TTM（需要该日期的单季值 + 前三个季度的单季值）
        # 但这里我们只检查该日期的单季值是否正确
        val = income_single.loc['2025-09-27', 'net_income']
        print(f"\n2025-09-27 的补全净收入: {val:,.0f} (期望 27,466,000,000)")

if __name__ == "__main__":
    test_secfin_quarterly_fix("AAPL")
