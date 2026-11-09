#!/usr/bin/env python
"""
详细测试 ben_graham 功能：
- 数据获取（年度指标、行项目、市值）
- 子分析函数（盈利稳定性、财务实力、估值）
- 综合评分和信号
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
# 导入 ben_graham 的分析函数
from valueagents.agents.src.analysts.ben_graham import (
    analyze_earnings_stability,
    analyze_financial_strength,
    analyze_valuation_graham,
)

def test_ticker(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 Ben Graham 分析: {ticker}")
    print(f"{'='*80}")

    # 1. 获取年度财务指标（limit=10 以获取足够历史）
    print("\n--- 1. 获取年度财务指标 (get_financial_metrics) ---")
    metrics = get_financial_metrics(ticker, end_date, period="annual", limit=10)
    if not metrics:
        print("❌ 未获取到 metrics")
        return
    print(f"✅ 获取到 {len(metrics)} 个年度数据点")
    latest = metrics[0]
    print(f"最新报告期: {latest.report_period}")
    # 检查关键字段
    print(f"EPS (最新): {latest.earnings_per_share}")
    print(f"Book Value per Share: {latest.book_value_per_share}")
    print(f"Total Assets: {latest.total_assets}")
    print(f"Total Liabilities: {latest.total_liabilities}")
    print(f"Current Assets: {latest.current_assets}")
    print(f"Current Liabilities: {latest.current_liabilities}")
    print(f"Market Cap: {latest.market_cap}")

    # 2. 获取年度行项目（用于股息、更多财务细节）
    print("\n--- 2. 获取年度行项目 (search_line_items) ---")
    line_items = search_line_items(
        ticker,
        [
            "earnings_per_share",
            "revenue",
            "net_income",
            "book_value_per_share",
            "total_assets",
            "total_liabilities",
            "current_assets",
            "current_liabilities",
            "dividends_and_other_cash_distributions",
            "outstanding_shares",
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
    print(f"最新行项目报告期: {latest_li.report_period}")
    print(f"EPS: {latest_li.earnings_per_share}")
    print(f"BVPS: {latest_li.book_value_per_share}")
    print(f"Current Assets: {latest_li.current_assets}")
    print(f"Current Liabilities: {latest_li.current_liabilities}")
    print(f"Dividends: {latest_li.dividends_and_other_cash_distributions}")

    # 3. 获取市值（用于估值）
    print("\n--- 3. 获取市值 (get_market_cap) ---")
    market_cap = get_market_cap(ticker, end_date)
    print(f"市值: {market_cap}")

    # 4. 运行子分析
    print("\n--- 4. 盈利稳定性分析 (analyze_earnings_stability) ---")
    earnings_result = analyze_earnings_stability(metrics, line_items)
    print(f"评分: {earnings_result['score']}/3 (附加分?)")  # 注意：score 最大为 4（因为可能加1分）
    print(f"细节: {earnings_result['details']}")

    print("\n--- 5. 财务实力分析 (analyze_financial_strength) ---")
    strength_result = analyze_financial_strength(line_items)
    print(f"评分: {strength_result['score']}/5 (附加分?)")  # 最大得分 2+2+1=5
    print(f"细节: {strength_result['details']}")

    print("\n--- 6. 格雷厄姆估值分析 (analyze_valuation_graham) ---")
    valuation_result = analyze_valuation_graham(line_items, market_cap)
    print(f"评分: {valuation_result['score']}/7 (附加分?)")  # 最大得分 4+3=7
    print(f"细节: {valuation_result['details']}")

    # 7. 综合评分和信号
    total_score = earnings_result['score'] + strength_result['score'] + valuation_result['score']
    max_possible = 15  # 根据 ben_graham.py 中的 max_possible_score
    print("\n--- 7. 综合评分 ---")
    print(f"总分: {total_score} / {max_possible}")
    if total_score >= 0.7 * max_possible:
        signal = "bullish"
    elif total_score <= 0.3 * max_possible:
        signal = "bearish"
    else:
        signal = "neutral"
    print(f"模拟信号: {signal}")

    # 8. 合理性检查
    print("\n--- 8. 合理性检查 ---")
    # 检查关键数据是否缺失
    issues = []
    if latest.earnings_per_share is None:
        issues.append("EPS 缺失")
    if latest.book_value_per_share is None:
        issues.append("BVPS 缺失")
    if latest.current_assets is None or latest.current_liabilities is None:
        issues.append("流动比率数据缺失")
    if market_cap is None:
        issues.append("市值缺失")
    if issues:
        print("⚠️  存在问题: " + "; ".join(issues))
    else:
        print("✅ 所有关键数据完整")

    # 检查估值合理性：如果 Graham Number 远低于股价，可能高估
    if valuation_result.get('details') and 'Graham Number' in valuation_result['details']:
        # 提取 Graham Number（从细节字符串中解析）
        import re
        match = re.search(r'Graham Number = ([\d,]+\.?\d*)', valuation_result['details'])
        if match:
            graham_num = float(match.group(1).replace(',', ''))
            if latest_li.outstanding_shares:
                current_price = market_cap / latest_li.outstanding_shares if market_cap and latest_li.outstanding_shares else None
                if current_price:
                    print(f"当前股价: {current_price:.2f}, Graham Number: {graham_num:.2f}")
                    if graham_num < current_price:
                        print("⚠️  股价高于 Graham Number，可能高估")
                    else:
                        print("✅ 股价低于 Graham Number，可能存在安全边际")

    print("\n" + "-"*80)

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_ticker(t)
