#!/usr/bin/env python
"""
全面测试 phil_fisher_agent
"""

import sys
import os
import json
import re
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# 强制使用 EDGAR（默认已启用，但为保险设置）
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "true"

# 重新加载 api 模块
import importlib
import valueagents.agents.src.tools.api as api
importlib.reload(api)

from valueagents.agents.src.analysts.phil_fisher import phil_fisher_agent
from valueagents.agents.src.tools.api import search_line_items, get_market_cap, get_insider_trades, get_company_news
from valueagents.agents.src.analysts.phil_fisher import (
    analyze_fisher_growth_quality,
    analyze_margins_stability,
    analyze_management_efficiency_leverage,
    analyze_fisher_valuation,
    analyze_insider_activity,
    analyze_sentiment,
)

def test_sub_analyses(ticker, end_date="2026-07-23"):
    """测试子分析函数，输出各项得分"""
    print(f"\n{'='*80}")
    print(f"子分析测试: {ticker}")
    print(f"{'='*80}")

    # 获取行项目（使用 EDGAR）
    fields = [
        "revenue",
        "net_income",
        "earnings_per_share",
        "free_cash_flow",
        "research_and_development",
        "operating_income",
        "operating_margin",
        "gross_margin",
        "total_debt",
        "shareholders_equity",
        "cash_and_equivalents",
        "ebit",
        "ebitda",
    ]
    line_items = search_line_items(ticker, fields, end_date, period="annual", limit=5, api_key=None)
    if not line_items:
        print("❌ 无法获取行项目")
        return

    market_cap = get_market_cap(ticker, end_date)
    if not market_cap:
        print("❌ 无法获取市值")
        return

    insider_trades = get_insider_trades(ticker, end_date, limit=50, api_key=None)
    company_news = get_company_news(ticker, end_date, limit=50, api_key=None)

    # 运行子分析
    growth = analyze_fisher_growth_quality(line_items)
    margins = analyze_margins_stability(line_items)
    mgmt = analyze_management_efficiency_leverage(line_items)
    valuation = analyze_fisher_valuation(line_items, market_cap)
    insider = analyze_insider_activity(insider_trades)
    sentiment = analyze_sentiment(company_news)

    print("子分析得分 (满分10分):")
    print(f"  增长与质量: {growth['score']:.2f} - {growth['details']}")
    print(f"  利润率稳定性: {margins['score']:.2f} - {margins['details']}")
    print(f"  管理层效率: {mgmt['score']:.2f} - {mgmt['details']}")
    print(f"  估值: {valuation['score']:.2f} - {valuation['details']}")
    print(f"  内幕: {insider['score']:.2f} - {insider['details']}")
    print(f"  情绪: {sentiment['score']:.2f} - {sentiment['details']}")

    # 加权总分
    total_score = (
        growth["score"] * 0.30
        + margins["score"] * 0.25
        + mgmt["score"] * 0.20
        + valuation["score"] * 0.15
        + insider["score"] * 0.05
        + sentiment["score"] * 0.05
    )
    print(f"加权总分: {total_score:.2f}/10")
    if total_score >= 7.5:
        signal = "bullish"
    elif total_score <= 4.5:
        signal = "bearish"
    else:
        signal = "neutral"
    print(f"计算信号: {signal}")

def test_full_agent(ticker, end_date="2026-07-23"):
    """测试完整的 agent 执行"""
    print(f"\n{'='*80}")
    print(f"完整 Agent 测试: {ticker}")
    print(f"{'='*80}")

    state = {
        "data": {
            "end_date": end_date,
            "tickers": [ticker],
            "analyst_signals": {}
        },
        "metadata": {"show_reasoning": False}
    }

    try:
        result = phil_fisher_agent(state)
        signals = state["data"]["analyst_signals"].get("phil_fisher_agent", {})
        if signals and ticker in signals:
            sig = signals[ticker]
            print(f"信号: {sig['signal']}")
            print(f"置信度: {sig['confidence']}")
            print("推理文本:")
            print(sig['reasoning'])
        else:
            print("❌ 未生成信号")
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_sub_analyses(t)
        test_full_agent(t)
