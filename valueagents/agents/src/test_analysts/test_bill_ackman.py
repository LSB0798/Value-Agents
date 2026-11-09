#!/usr/bin/env python
"""
全面测试 Bill Ackman 分析师的功能与合理性。
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
# 导入 Bill Ackman 的子分析函数
from valueagents.agents.src.analysts.bill_ackman import (
    analyze_business_quality,
    analyze_financial_discipline,
    analyze_activism_potential,
    analyze_valuation,
)

def test_ticker(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 Bill Ackman 分析: {ticker}")
    print(f"{'='*80}")

    # 1. 获取年度财务指标（用于 ROE）
    metrics = get_financial_metrics(ticker, end_date, period="annual", limit=5)
    if not metrics:
        print("❌ 未获取到 metrics")
        return
    print(f"✅ 获取到 {len(metrics)} 个年度数据点")
    latest_metric = metrics[0]
    print(f"最新 ROE: {latest_metric.return_on_equity:.2%}" if latest_metric.return_on_equity else "ROE: None")

    # 2. 获取年度行项目
    line_items = search_line_items(
        ticker,
        [
            "revenue",
            "operating_margin",
            "debt_to_equity",
            "free_cash_flow",
            "total_assets",
            "total_liabilities",
            "dividends_and_other_cash_distributions",
            "outstanding_shares",
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
    print(f"最新 FCF: {latest_li.free_cash_flow}")
    print(f"最新营收: {latest_li.revenue}")
    print(f"最新运营利润率: {latest_li.operating_margin}")

    # 3. 获取市值
    market_cap = get_market_cap(ticker, end_date)
    print(f"市值: {market_cap}")

    # 4. 运行子分析
    print("\n--- 业务质量分析 (Business Quality) ---")
    quality = analyze_business_quality(metrics, line_items)
    print(f"评分: {quality['score']}")
    print(f"细节: {quality['details']}")

    print("\n--- 财务纪律分析 (Financial Discipline) ---")
    discipline = analyze_financial_discipline(metrics, line_items)
    print(f"评分: {discipline['score']}")
    print(f"细节: {discipline['details']}")

    print("\n--- 激进潜力分析 (Activism Potential) ---")
    activism = analyze_activism_potential(line_items)
    print(f"评分: {activism['score']}")
    print(f"细节: {activism['details']}")

    print("\n--- 估值分析 (Valuation) ---")
    valuation = analyze_valuation(line_items, market_cap)
    print(f"评分: {valuation['score']}")
    print(f"细节: {valuation['details']}")
    if valuation.get('intrinsic_value'):
        print(f"内在价值: {valuation['intrinsic_value']:,.0f}")
        print(f"安全边际: {valuation['margin_of_safety']:.2%}")

    # 5. 综合评分和信号
    total = quality['score'] + discipline['score'] + activism['score'] + valuation['score']
    max_possible = 20
    print(f"\n--- 综合评分: {total} / {max_possible} ---")
    if total >= 0.7 * max_possible:
        signal = "bullish"
    elif total <= 0.3 * max_possible:
        signal = "bearish"
    else:
        signal = "neutral"
    print(f"模拟信号: {signal}")

    # 6. 合理性检查 (基于数值含义)
    print("\n--- 合理性检查 ---")
    issues = []

    # 检查关键字段是否缺失
    if latest_li.revenue is None:
        issues.append("营收缺失")
    if latest_li.free_cash_flow is None:
        issues.append("FCF缺失")
    if latest_li.operating_margin is None:
        issues.append("运营利润率缺失")
    if market_cap is None:
        issues.append("市值缺失")

    # 检查业务质量评分是否与数据一致
    if quality['score'] > 0:
        # 检查是否有收入增长、运营利润率、FCF正数、ROE高
        if 'Revenue grew' in quality['details']:
            print("✅ 有收入增长")
        else:
            print("⚠️  收入增长不明显")
        if 'Operating margins have often exceeded 15%' in quality['details']:
            print("✅ 运营利润率良好")
        else:
            print("⚠️  运营利润率偏低")
        if 'High ROE' in quality['details']:
            print("✅ ROE 较高")
        else:
            print("⚠️  ROE 一般")
    else:
        print("⚠️  业务质量评分为0，可能数据不足或基本面弱")

    # 财务纪律评分检查
    if discipline['score'] > 0:
        if 'Debt-to-equity < 1.0' in discipline['details'] or 'Liabilities-to-assets < 50%' in discipline['details']:
            print("✅ 财务杠杆合理")
        else:
            print("⚠️  财务杠杆偏高")
        if 'history of returning capital' in discipline['details']:
            print("✅ 有股东回报")
        else:
            print("⚠️  股东回报不足")
        if 'decreased over time' in discipline['details']:
            print("✅ 股票回购")
        else:
            print("⚠️  无股票回购或稀释")
    else:
        print("⚠️  财务纪律评分低")

    # 激进潜力: 若收入增长>15%且利润率<10%，应有分数
    if activism['score'] > 0:
        print("✅ 存在激进潜力 (收入增长快但利润率低)")
    else:
        print("⚠️  无明显激进潜力")

    # 估值: 若安全边际>30%则有得分
    if valuation['score'] > 0:
        print("✅ 估值有吸引力 (安全边际高)")
    else:
        print("⚠️  估值偏高或数据不足")

    if issues:
        print("❌ 存在数据缺失: " + "; ".join(issues))
    else:
        print("✅ 所有关键数据完整")

    # 额外: 打印估值的安全边际具体数值
    if valuation.get('margin_of_safety') is not None:
        mos = valuation['margin_of_safety']
        if mos > 0.3:
            print(f"✅ 安全边际 {mos:.2%} 超过30%，估值评分合理")
        elif mos > 0.1:
            print(f"⚠️  安全边际 {mos:.2%} 介于10-30%，估值得分较低")
        else:
            print(f"⚠️  安全边际 {mos:.2%} 低于10%，估值无吸引力")

if __name__ == "__main__":
    # 测试多个股票
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_ticker(t)
