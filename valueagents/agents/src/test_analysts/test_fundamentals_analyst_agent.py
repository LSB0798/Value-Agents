#!/usr/bin/env python
"""
测试 fundamentals_analyst_agent 的数据需求和功能
"""

import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_financial_metrics
from valueagents.agents.src.analysts.fundamentals import fundamentals_analyst_agent
from valueagents.agents.src.graph.state import AgentState

def test_fundamentals(ticker="AAPL", end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 fundamentals_analyst_agent 所需数据: {ticker}")
    print(f"{'='*80}")

    # 获取财务指标
    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=5)
    if not metrics:
        print("❌ 无法获取 metrics")
        return

    latest = metrics[0]
    print(f"最新报告期: {latest.report_period}")

    # 检查所有 fundamentals_analyst_agent 需要的字段
    required_fields = [
        'return_on_equity', 'net_margin', 'operating_margin',
        'revenue_growth', 'earnings_growth', 'book_value_growth',
        'current_ratio', 'debt_to_equity',
        'free_cash_flow_per_share', 'earnings_per_share',
        'price_to_earnings_ratio', 'price_to_book_ratio', 'price_to_sales_ratio'
    ]
    missing = []
    for field in required_fields:
        if getattr(latest, field, None) is None:
            missing.append(field)
    if missing:
        print(f"⚠️ 缺失字段: {missing}")
    else:
        print("✅ 所有必需字段均存在")

    # 打印字段值
    print("\n关键字段值:")
    for field in required_fields:
        value = getattr(latest, field)
        if isinstance(value, float):
            print(f"  {field}: {value:.4f}")
        else:
            print(f"  {field}: {value}")

    # 模拟 AgentState 以运行 fundamentals_analyst_agent
    state = {
        "data": {
            "end_date": end_date,
            "tickers": [ticker],
            "analyst_signals": {}
        },
        "metadata": {"show_reasoning": False}
    }
    # 设置 api_key（如果必要，可以传入空）
    # 但 fundamentals_analyst_agent 会从 state 中获取 api_key，我们不在 state 中设置，它会从环境变量读取

    # 运行 agent
    print("\n运行 fundamentals_analyst_agent...")
    result = fundamentals_analyst_agent(state)
    signals = state["data"]["analyst_signals"].get("fundamentals_analyst_agent", {})
    if signals and ticker in signals:
        sig = signals[ticker]
        print(f"信号: {sig['signal']}")
        print(f"置信度: {sig['confidence']}")
        print("推理细节:")
        pprint(sig['reasoning'])
    else:
        print("❌ 未生成信号")

if __name__ == "__main__":
    test_fundamentals("AAPL")
