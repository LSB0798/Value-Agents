#!/usr/bin/env python
"""
测试 aswath_damodaran 分析结果的合理性
"""

import sys
import os
import json
import math
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import (
    get_financial_metrics,
    search_line_items,
    get_market_cap,
)
from valueagents.agents.src.analysts.aswath_damodaran import (
    analyze_growth_and_reinvestment,
    analyze_risk_profile,
    analyze_relative_valuation,
    calculate_intrinsic_value_dcf,
)

def test_ticker(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 aswath_damodaran 分析: {ticker}")
    print(f"{'='*80}")

    # 获取数据
    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=5)
    if not metrics:
        print("❌ 无法获取 metrics")
        return
    line_items = search_line_items(
        ticker,
        [
            "free_cash_flow",
            "ebit",
            "interest_expense",
            "capital_expenditure",
            "depreciation_and_amortization",
            "outstanding_shares",
            "net_income",
            "total_debt",
        ],
        end_date,
        period="ttm",
        limit=5,
    )
    market_cap = get_market_cap(ticker, end_date)

    print(f"获取到 {len(metrics)} 个 TTM 数据点")
    latest = metrics[0]
    print(f"最新报告期: {latest.report_period}")
    print(f"Revenue: {latest.revenue:,.0f}" if latest.revenue else "Revenue: None")
    print(f"Free Cash Flow: {latest.free_cash_flow:,.0f}" if latest.free_cash_flow else "FCF: None")
    print(f"EBIT: {latest.ebit:,.0f}" if latest.ebit else "EBIT: None")
    print(f"ROIC: {latest.return_on_invested_capital:.2%}" if latest.return_on_invested_capital else "ROIC: None")
    print(f"Debt/Equity: {latest.debt_to_equity:.2f}" if latest.debt_to_equity else "D/E: None")
    print(f"Beta: {latest.beta:.2f}" if latest.beta else "Beta: None")
    print(f"PE: {latest.price_to_earnings_ratio:.2f}" if latest.price_to_earnings_ratio else "PE: None")
    print(f"Market Cap: {market_cap:,.0f}" if market_cap else "Market Cap: None")

    # 1. 增长分析
    print("\n--- 1. 增长与再投资分析 ---")
    growth_result = analyze_growth_and_reinvestment(metrics, line_items)
    print(f"评分: {growth_result['score']}/{growth_result['max_score']}")
    print(f"细节: {growth_result['details']}")
    # 检查是否合理
    if 'Revenue CAGR' in growth_result['details']:
        cagr_str = [p for p in growth_result['details'].split(';') if 'Revenue CAGR' in p]
        if cagr_str:
            # cagr = float(cagr_str[0].split(' ')[-1].replace('%', ''))
            import re
            if cagr_str:
                match = re.search(r'(\d+\.?\d*)%', cagr_str[0])
                if match:
                    cagr = float(match.group(1))
                else:
                    cagr = None
            print(f"  Revenue CAGR: {cagr:.1f}%")
            # 对于成熟公司，CAGR 一般在 0-15% 之间
            if cagr < 0:
                print("  ⚠️  Revenue CAGR 为负，可能公司收缩")
            elif cagr > 30:
                print("  ⚠️  Revenue CAGR 过高，需检查数据")
            else:
                print("  ✅ Revenue CAGR 在合理范围")

    # 2. 风险分析
    print("\n--- 2. 风险分析 ---")
    risk_result = analyze_risk_profile(metrics, line_items)
    print(f"评分: {risk_result['score']}/{risk_result['max_score']}")
    print(f"细节: {risk_result['details']}")
    print(f"Beta: {risk_result.get('beta', 'N/A')}")
    print(f"Cost of Equity: {risk_result.get('cost_of_equity', 'N/A')}")

    # 3. 相对估值
    print("\n--- 3. 相对估值分析 ---")
    rel_val_result = analyze_relative_valuation(metrics)
    print(f"评分: {rel_val_result['score']}/{rel_val_result['max_score']}")
    print(f"细节: {rel_val_result['details']}")
    if 'Insufficient' in rel_val_result['details']:
        print("  ⚠️  PE 历史数据不足，相对估值评分可能不准确")
        print("  建议: 增加 limit 或使用行业平均 PE")

    # 4. DCF 估值
    print("\n--- 4. DCF 估值 ---")
    intrinsic_result = calculate_intrinsic_value_dcf(metrics, line_items, risk_result)
    if intrinsic_result.get('intrinsic_value'):
        iv = intrinsic_result['intrinsic_value']
        print(f"内在价值 (企业价值): {iv:,.0f}")
        print(f"每股内在价值: {intrinsic_result.get('intrinsic_per_share', 'N/A')}")
        if market_cap:
            print(f"当前市值: {market_cap:,.0f}")
            mos = (iv - market_cap) / market_cap if market_cap else None
            print(f"安全边际 (MOS): {mos:.2%}" if mos is not None else "MOS: N/A")
            if mos is not None:
                if mos > 0.25:
                    print("  ✅ 安全边际充足 (>25%)")
                elif mos > 0:
                    print("  ⚠️  安全边际较小 (0-25%)")
                else:
                    print("  ⚠️  安全边际为负，当前估值偏高")
    else:
        print("  ❌ DCF 计算失败，可能缺少关键数据")

    # 5. 最终信号 (模拟 agent 的逻辑)
    print("\n--- 5. 模拟最终信号 ---")
    total_score = growth_result['score'] + risk_result['score'] + rel_val_result['score']
    max_score = growth_result['max_score'] + risk_result['max_score'] + rel_val_result['max_score']
    print(f"总评分: {total_score}/{max_score}")
    if intrinsic_result.get('intrinsic_value') and market_cap:
        mos = (intrinsic_result['intrinsic_value'] - market_cap) / market_cap
        if mos >= 0.25:
            signal = "bullish"
        elif mos <= -0.25:
            signal = "bearish"
        else:
            signal = "neutral"
        print(f"Margin of Safety: {mos:.2%}")
        print(f"信号: {signal}")
        # 检查信号是否合理
        if ticker in ['AAPL', 'MSFT'] and mos < 0:
            # 这些是大型科技股，通常估值较高
            if signal == 'bearish':
                print("  ✅ 信号合理: 估值较高，符合当前市场")
            else:
                print("  ⚠️  信号可能偏乐观，需进一步验证")
        elif ticker in ['TSLA'] and mos < -0.3:
            if signal == 'bearish':
                print("  ✅ 信号合理: 高增长但估值过高")
            else:
                print("  ⚠️  信号可能偏乐观")
    else:
        print("无法计算安全边际，信号不确定")

if __name__ == "__main__":
    for ticker in ["AAPL", "MSFT", "GOOGL", "TSLA"]:
        test_ticker(ticker)
        print("\n" + "-"*80)
