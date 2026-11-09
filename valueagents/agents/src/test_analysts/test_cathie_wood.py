#!/usr/bin/env python
"""
全面测试 Cathie Wood 分析师的功能与合理性。
验证 EDGAR/yfinance 数据是否满足其分析需求，并检查子分析评分是否合理。
"""

import sys
import os
import math
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import (
    get_financial_metrics,
    search_line_items,
    get_market_cap,
)
# 导入 Cathie Wood 的子分析函数
from valueagents.agents.src.analysts.cathie_wood import (
    analyze_disruptive_potential,
    analyze_innovation_growth,
    analyze_cathie_wood_valuation,
)

def test_ticker(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 Cathie Wood 分析: {ticker}")
    print(f"{'='*80}")

    # 1. 获取年度财务指标（用于 ROE，但 cathie_wood 不直接使用 metrics，而是用 line_items）
    metrics = get_financial_metrics(ticker, end_date, period="annual", limit=5)
    if not metrics:
        print("❌ 未获取到 metrics")
        return
    print(f"✅ 获取到 {len(metrics)} 个年度数据点")

    # 2. 获取年度行项目（cathie_wood 主要使用这些）
    line_items = search_line_items(
        ticker,
        [
            "revenue",
            "gross_margin",
            "operating_margin",
            "debt_to_equity",
            "free_cash_flow",
            "total_assets",
            "total_liabilities",
            "dividends_and_other_cash_distributions",
            "outstanding_shares",
            "research_and_development",
            "capital_expenditure",
            "operating_expense",
        ],
        end_date,
        period="annual",
        limit=5,
    )
    if not line_items:
        print("❌ 未获取到 line_items")
        return
    print(f"✅ 获取到 {len(line_items)} 条行项目记录")
    latest_li = line_items[0]
    print(f"最新报告期: {latest_li.report_period}")
    print(f"营收: {latest_li.revenue}")
    print(f"毛利率: {getattr(latest_li, 'gross_margin', None)}")
    print(f"营业利润率: {getattr(latest_li, 'operating_margin', None)}")
    print(f"研发费用: {getattr(latest_li, 'research_and_development', None)}")
    print(f"资本支出: {getattr(latest_li, 'capital_expenditure', None)}")
    print(f"营业费用: {getattr(latest_li, 'operating_expense', None)}")
    print(f"自由现金流: {latest_li.free_cash_flow}")

    # 3. 获取市值
    market_cap = get_market_cap(ticker, end_date)
    print(f"市值: {market_cap}")

    # 4. 运行子分析
    print("\n--- 颠覆性潜力分析 (Disruptive Potential) ---")
    disruptive = analyze_disruptive_potential(metrics, line_items)
    print(f"评分: {disruptive['score']:.2f} / 5")
    print(f"细节: {disruptive['details']}")
    if 'raw_score' in disruptive:
        print(f"原始分: {disruptive['raw_score']}, 最大原始分: {disruptive['max_score']}")

    print("\n--- 创新增长分析 (Innovation Growth) ---")
    innovation = analyze_innovation_growth(metrics, line_items)
    print(f"评分: {innovation['score']:.2f} / 5")
    print(f"细节: {innovation['details']}")
    if 'raw_score' in innovation:
        print(f"原始分: {innovation['raw_score']}, 最大原始分: {innovation['max_score']}")

    print("\n--- 估值分析 (Valuation) ---")
    valuation = analyze_cathie_wood_valuation(line_items, market_cap)
    print(f"评分: {valuation['score']} / 3")
    print(f"细节: {valuation['details']}")
    if valuation.get('intrinsic_value'):
        print(f"内在价值: {valuation['intrinsic_value']:,.0f}")
        print(f"安全边际: {valuation['margin_of_safety']:.2%}")

    # 5. 综合评分和信号（与 cathie_wood_agent 逻辑一致）
    total = disruptive['score'] + innovation['score'] + valuation['score']
    max_possible = 15
    print(f"\n--- 综合评分: {total:.2f} / {max_possible} ---")
    if total >= 0.7 * max_possible:
        signal = "bullish"
    elif total <= 0.3 * max_possible:
        signal = "bearish"
    else:
        signal = "neutral"
    print(f"模拟信号: {signal}")

    # 6. 合理性检查（基于数值含义）
    print("\n--- 合理性检查 ---")
    issues = []

    # 检查关键字段是否缺失
    if latest_li.revenue is None:
        issues.append("营收缺失")
    if latest_li.free_cash_flow is None:
        issues.append("FCF缺失")
    if getattr(latest_li, 'gross_margin', None) is None:
        issues.append("毛利率缺失")
    if getattr(latest_li, 'research_and_development', None) is None:
        issues.append("研发费用缺失")
    if market_cap is None:
        issues.append("市值缺失")

    # 检查 disruptive 评分合理性
    if disruptive['score'] > 3:
        print("✅ 颠覆性潜力评分较高 (可能因高增长/高研发)")
    else:
        print("⚠️  颠覆性潜力评分偏低 (可能因增长或研发不足)")

    # 检查 innovation 评分合理性
    if innovation['score'] > 3:
        print("✅ 创新增长评分较高 (可能因R&D投入、FCF等)")
    else:
        print("⚠️  创新增长评分偏低")

    # 检查估值评分：若安全边际>0.2或0.5，估值应有分
    if valuation['score'] > 0:
        print("✅ 估值有吸引力 (安全边际较高)")
    else:
        print("⚠️  估值无吸引力 (安全边际较低或为负)")

    if issues:
        print("❌ 存在数据缺失: " + "; ".join(issues))
    else:
        print("✅ 所有关键数据完整")

    # 额外打印估值细节
    if valuation.get('margin_of_safety') is not None:
        mos = valuation['margin_of_safety']
        if mos > 0.5:
            print(f"✅ 安全边际 {mos:.2%} 超过50%，估值得分高")
        elif mos > 0.2:
            print(f"⚠️  安全边际 {mos:.2%} 介于20-50%，估值得分一般")
        else:
            print(f"⚠️  安全边际 {mos:.2%} 低于20%，估值无吸引力")

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_ticker(t)
