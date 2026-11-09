#!/usr/bin/env python
"""
详细调试 TTM 计算，比较 secfin 内置 TTM 与手动差分方法。
"""

import pandas as pd
from secfin import SECClient, Company

def debug_ttm(ticker="AAPL"):
    client = SECClient("ValueAgents research contact@example.com")
    company = Company(ticker, client)

    # 获取季度数据（累计值）
    income_q = company.get_income_statement(period='quarterly').to_dataframe()
    balance_q = company.get_balance_sheet(period='quarterly').to_dataframe()

    income_q.index = pd.to_datetime(income_q.index)
    balance_q.index = pd.to_datetime(balance_q.index)

    income_q = income_q.sort_index()
    balance_q = balance_q.sort_index()

    # 获取年度数据用于参考
    income_a = company.get_income_statement(period='annual').to_dataframe()
    income_a.index = pd.to_datetime(income_a.index)
    income_a = income_a.sort_index()

    print("=" * 80)
    print("secfin 内置 TTM 方法的结果:")
    income_obj = company.get_income_statement()
    ttm_ni = income_obj.net_income.ttm()
    print(f"TTM 净收入: {ttm_ni:,.0f}\n")

    # 手动方法：使用差分
    print("手动差分方法详细步骤:")
    # 转换为单季值
    income_single = income_q.diff().fillna(income_q)
    
    # 只取 net_income 列
    ni_q = income_q['net_income']
    ni_single = income_single['net_income']

    print("最近 8 个季度的原始累计净收入 (net_income):")
    print(ni_q.tail(8).to_string())
    print("\n对应的单季净收入 (差分):")
    print(ni_single.tail(8).to_string())

    # 手动计算 TTM（最近四个季度）
    # 取最后四个单季值求和
    last_four = ni_single.tail(4)
    manual_ttm = last_four.sum()
    print(f"\n手动计算的 TTM 净收入 (最近四个单季值之和): {manual_ttm:,.0f}")
    print(f"使用的季度: {last_four.index.strftime('%Y-%m-%d').tolist()}")

    # 检查最近四个单季值是否对应正确的财年 Q4 等
    # 打印年度数据
    print("\n年度净收入 (最近几年):")
    print(income_a['net_income'].tail(3).to_string())

    # 检查是否因为财年 Q4 缺失导致手动方法不同
    # 尝试用年度数据来验证单季值
    # 例如，2025 财年 Q4 = 年度 - Q1-Q2-Q3
    # 先看 2025 年
    fy_2025 = income_a.loc[income_a.index.year == 2025, 'net_income'].iloc[0] if 2025 in income_a.index.year else None
    if fy_2025 is not None:
        # 获取 Q1, Q2, Q3 的单季值 (2024-12-28, 2025-03-29, 2025-06-28)
        q1 = ni_single.loc['2024-12-28'] if '2024-12-28' in ni_single.index else None
        q2 = ni_single.loc['2025-03-29'] if '2025-03-29' in ni_single.index else None
        q3 = ni_single.loc['2025-06-28'] if '2025-06-28' in ni_single.index else None
        if all(v is not None for v in [q1, q2, q3]):
            q4_reconstructed = fy_2025 - q1 - q2 - q3
            print(f"\n2025 财年数据:")
            print(f"  年度净收入: {fy_2025:,.0f}")
            print(f"  Q1: {q1:,.0f}, Q2: {q2:,.0f}, Q3: {q3:,.0f}")
            print(f"  推算 Q4: {q4_reconstructed:,.0f}")
            # 重新计算 TTM (Q4 + Q1 + Q2 + Q3 of next year? 需要明确窗口)
            # 但我们现在手动 TTM 用的是 2025-06-28, 2025-09-27, 2025-12-27, 2026-03-28
            # 这些季度中，2025-09-27 是财年结束，但 income_single 在这个日期是 NaN，因为它是财年末，没有单独季度数据。
            # 所以我们之前的 TTM 跳过了这个日期？检查 ni_single 在 2025-09-27 的值。
            if '2025-09-27' in ni_single.index:
                print(f"2025-09-27 单季净收入: {ni_single.loc['2025-09-27']}")
            else:
                print("2025-09-27 不存在于单季数据中 (因为财年末无单独季度报告)")

    print("\n可能的问题:")
    print("1. 手动方法使用了 2025-09-27 的单季值，但这个值可能为 NaN 或不正确 (因为财年末无单独季度数据)。")
    print("2. 手动方法没有正确跳过财年末的季度，导致使用了错误的数据点。")
    print("3. 手动 TTM 窗口应与 secfin 内置 TTM 的窗口一致。secfin 的 ttm() 可能返回的是基于最新四个季度 (可能包括财年 Q4 补全) 的值。")

if __name__ == "__main__":
    debug_ttm("AAPL")
