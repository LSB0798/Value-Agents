#!/usr/bin/env python
"""
全面测试 michael_burry_agent
"""

import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.analysts.michael_burry import michael_burry_agent

def test_burry_agent(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 michael_burry_agent: {ticker}")
    print(f"{'='*80}")

    # 创建模拟 state
    state = {
        "data": {
            "end_date": end_date,
            "tickers": [ticker],
            "analyst_signals": {}
        },
        "metadata": {"show_reasoning": False}
    }

    # 运行 agent
    try:
        result = michael_burry_agent(state)
        signals = state["data"]["analyst_signals"].get("michael_burry_agent", {})
        if signals and ticker in signals:
            sig = signals[ticker]
            print(f"最终信号: {sig['signal']}")
            print(f"置信度: {sig['confidence']}")
            print(f"推理: {sig['reasoning']}")
        else:
            print("❌ 未生成信号")
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

    # 额外打印子分析数据（在 agent 内部已存储，但未暴露；我们可以重新调用子分析函数，但为了简洁，此处只打印最终结果）
    # 若要查看子分析，可修改 agent 使其返回分析数据，或我们单独调用子分析函数测试，但此处不重复。

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_burry_agent(t)
