#!/usr/bin/env python
"""
使用 EDGAR 数据补全 Q4，生成完整的滚动 TTM 序列。
"""

import pandas as pd
from secfin import SECClient, Company

def build_ttm_sequence(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)

    # 获取季度数据（累计值）
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    income_q.index = pd.to_datetime(income_q.index)
    income_q = income_q.sort_index()

    # 获取年度数据
    income_a = company.get_income_statement(period='annual').to_dataframe()
    income_a.index = pd.to_datetime(income_a.index)
    income_a = income_a.sort_index()

    # 创建完整的时间索引：包含所有季度和年度日期
    all_dates = income_q.index.union(income_a.index)
    all_dates = all_dates.sort_values()

    # 创建一个空的DataFrame，索引为所有日期
    income_full = pd.DataFrame(index=all_dates, columns=income_q.columns)

    # 先用季度累计值填充
    income_full.loc[income_q.index] = income_q

    # 用年度累计值填充财年末（覆盖季度数据中可能存在的NaN）
    # 注意：年度数据在财年末，如果季度数据中没有该日期，则直接填充
    for a_date in income_a.index:
        if a_date in income_full.index:
            # 如果该日期在 income_full 中，但季度数据可能为NaN（因为Q4无季报）
            # 直接覆盖为年度值
            for col in income_a.columns:
                if col in income_full.columns:
                    income_full.loc[a_date, col] = income_a.loc[a_date, col]

    # 现在 income_full 包含完整的累计值序列（季度 + 年度）
    # 差分得到单季值
    income_single = income_full.diff().fillna(income_full)

    # 提取净收入列
    ni_single = income_single['net_income']

    # 滚动计算 TTM（4个季度）
    ttm_ni = ni_single.rolling(window=4).sum()

    # 打印最近几个 TTM
    print("最近 8 个 TTM 净收入:")
    print(ttm_ni.tail(8).to_string())

    # 验证 2025-09-27
    if '2025-09-27' in ttm_ni.index:
        val = ttm_ni.loc['2025-09-27']
        print(f"\n2025-09-27 的 TTM 净收入: {val:,.0f} (期望 112,010,000,000)")
        if abs(val - 112010000000) < 1000000:
            print("✅ 匹配！")
        else:
            print(f"❌ 差异: {val - 112010000000:,.0f}")

    # 打印 2026-03-28 的 TTM
    if '2026-03-28' in ttm_ni.index:
        val2 = ttm_ni.loc['2026-03-28']
        print(f"\n2026-03-28 的 TTM 净收入: {val2:,.0f}")

    return ttm_ni

if __name__ == "__main__":
    build_ttm_sequence("AAPL")
