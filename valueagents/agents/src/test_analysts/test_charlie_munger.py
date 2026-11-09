#!/usr/bin/env python
"""
全面测试 Charlie Munger 分析师的功能与合理性。
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
    get_insider_trades,
    get_company_news,
)
# 导入 Charlie Munger 的子分析函数
from valueagents.agents.src.analysts.charlie_munger import (
    analyze_moat_strength,
    analyze_management_quality,
    analyze_predictability,
    calculate_munger_valuation,
)

def test_ticker(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 Charlie Munger 分析: {ticker}")
    print(f"{'='*80}")

    # 1. 获取年度财务指标（用于 ROE 等，但 Munger 主要使用 line_items）
    metrics = get_financial_metrics(ticker, end_date, period="annual", limit=10)
    if not metrics:
        print("❌ 未获取到 metrics")
        return
    print(f"✅ 获取到 {len(metrics)} 个年度数据点")

    # 2. 获取年度行项目（Munger 分析的核心）
    line_items = search_line_items(
        ticker,
        [
            "revenue",
            "net_income",
            "operating_income",
            "return_on_invested_capital",
            "gross_margin",
            "operating_margin",
            "free_cash_flow",
            "capital_expenditure",
            "cash_and_equivalents",
            "total_debt",
            "shareholders_equity",
            "outstanding_shares",
            "research_and_development",
            "goodwill_and_intangible_assets",
        ],
        end_date,
        period="annual",
        limit=10,
    )
    if not line_items:
        print("❌ 未获取到 line_items")
        return
    print(f"✅ 获取到 {len(line_items)} 条行项目记录")
    latest_li = line_items[0]
    print(f"最新报告期: {latest_li.report_period}")
    # 打印关键字段
    print(f"营收: {latest_li.revenue}")
    print(f"净利润: {latest_li.net_income}")
    print(f"营业利润: {getattr(latest_li, 'operating_income', None)}")
    print(f"ROIC: {getattr(latest_li, 'return_on_invested_capital', None)}")
    print(f"毛利率: {getattr(latest_li, 'gross_margin', None)}")
    print(f"营业利润率: {getattr(latest_li, 'operating_margin', None)}")
    print(f"FCF: {latest_li.free_cash_flow}")
    print(f"总债务: {latest_li.total_debt}")
    print(f"股东权益: {latest_li.shareholders_equity}")
    print(f"商誉/无形资产: {getattr(latest_li, 'goodwill_and_intangible_assets', None)}")
    print(f"研发费用: {getattr(latest_li, 'research_and_development', None)}")
    print(f"资本支出: {getattr(latest_li, 'capital_expenditure', None)}")
    print(f"流通股: {latest_li.outstanding_shares}")

    # 3. 获取市值
    market_cap = get_market_cap(ticker, end_date)
    print(f"市值: {market_cap}")

    # 4. 获取内幕交易（用于管理质量）
    insider_trades = get_insider_trades(ticker, end_date, limit=100)
    print(f"内幕交易记录数: {len(insider_trades) if insider_trades else 0}")

    # 5. 获取公司新闻（用于定性，但 Munger 不直接评分）
    company_news = get_company_news(ticker, end_date, limit=10)
    print(f"新闻条数: {len(company_news) if company_news else 0}")

    # 6. 运行子分析
    print("\n--- 护城河强度分析 (Moat Strength) ---")
    moat = analyze_moat_strength(metrics, line_items)
    print(f"评分: {moat['score']:.2f} / 10")
    print(f"细节: {moat['details']}")

    print("\n--- 管理质量分析 (Management Quality) ---")
    mgmt = analyze_management_quality(line_items, insider_trades)
    print(f"评分: {mgmt['score']:.2f} / 10")
    print(f"细节: {mgmt['details']}")
    # 打印额外指标
    if 'insider_buy_ratio' in mgmt:
        print(f"内幕买入比例: {mgmt['insider_buy_ratio']:.2f}" if mgmt['insider_buy_ratio'] is not None else "内幕买入比例: N/A")
    if 'recent_de_ratio' in mgmt:
        print(f"最新 D/E: {mgmt['recent_de_ratio']:.2f}" if mgmt['recent_de_ratio'] is not None else "D/E: N/A")
    if 'cash_to_revenue' in mgmt:
        print(f"现金/营收: {mgmt['cash_to_revenue']:.2f}" if mgmt['cash_to_revenue'] is not None else "现金/营收: N/A")
    if 'share_count_trend' in mgmt:
        print(f"股份趋势: {mgmt['share_count_trend']}")

    print("\n--- 业务可预测性分析 (Predictability) ---")
    pred = analyze_predictability(line_items)
    print(f"评分: {pred['score']:.2f} / 10")
    print(f"细节: {pred['details']}")

    print("\n--- 估值分析 (Munger Valuation) ---")
    val = calculate_munger_valuation(line_items, market_cap)
    print(f"评分: {val['score']:.2f} / 10")
    print(f"细节: {val['details']}")
    if 'fcf_yield' in val:
        print(f"FCF 收益率: {val['fcf_yield']:.2%}" if val['fcf_yield'] is not None else "FCF 收益率: N/A")
    if 'intrinsic_value_range' in val:
        print(f"合理价值: {val['intrinsic_value_range']['reasonable']:,.0f}" if val['intrinsic_value_range']['reasonable'] else "合理价值: N/A")
    if 'margin_of_safety_vs_fair_value' in val:
        print(f"安全边际 (vs 合理价值): {val['margin_of_safety_vs_fair_value']:.2%}" if val['margin_of_safety_vs_fair_value'] is not None else "安全边际: N/A")

    # 7. 综合评分与信号（与分析师一致）
    total = moat['score'] * 0.35 + mgmt['score'] * 0.25 + pred['score'] * 0.25 + val['score'] * 0.15
    max_possible = 10
    print(f"\n--- 综合评分: {total:.2f} / {max_possible} ---")
    if total >= 7.5:
        signal = "bullish"
    elif total <= 5.5:
        signal = "bearish"
    else:
        signal = "neutral"
    print(f"模拟信号: {signal}")

    # 8. 合理性检查
    print("\n--- 合理性检查 ---")
    issues = []

    # 检查关键字段是否缺失
    if latest_li.revenue is None:
        issues.append("营收缺失")
    if latest_li.free_cash_flow is None:
        issues.append("FCF缺失")
    if getattr(latest_li, 'operating_income', None) is None:
        issues.append("营业利润缺失")
    if getattr(latest_li, 'return_on_invested_capital', None) is None:
        issues.append("ROIC缺失")
    if getattr(latest_li, 'goodwill_and_intangible_assets', None) is None:
        issues.append("商誉/无形资产缺失")
    if market_cap is None:
        issues.append("市值缺失")

    # 检查护城河评分：若 ROIC 高且稳定，评分应高
    if moat['score'] > 7:
        print("✅ 护城河强度评分较高 (ROIC 高/稳定，有定价权)")
    else:
        print("⚠️  护城河强度评分偏低 (可能 ROIC 不足或资本密集)")

    # 检查管理质量：若 FCF/NI 高、D/E 低、内幕买入多，评分应高
    if mgmt['score'] > 7:
        print("✅ 管理质量评分较高 (现金转化好、负债低、内幕一致)")
    else:
        print("⚠️  管理质量评分偏低")

    # 检查可预测性：若营收增长稳定，运营利润持续为正，评分应高
    if pred['score'] > 7:
        print("✅ 业务可预测性评分较高 (收入稳定、利润稳定)")
    else:
        print("⚠️  业务可预测性评分偏低")

    # 检查估值：若 FCF 收益率 >8% 或 MOS >30%，估值有吸引力
    if val['score'] > 7:
        print("✅ 估值有吸引力")
    else:
        print("⚠️  估值无吸引力或偏高")

    if issues:
        print("❌ 存在数据缺失: " + "; ".join(issues))
    else:
        print("✅ 所有关键数据完整")

if __name__ == "__main__":
    # tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    # tickers = ["AAPL", "MSFT"]
    tickers = ["GOOGL", "TSLA"]
    for t in tickers:
        test_ticker(t)
