#!/usr/bin/env python
"""
全面测试 peter_lynch_agent
"""

import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.analysts.peter_lynch import peter_lynch_agent

def test_peter_lynch(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 peter_lynch_agent: {ticker}")
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

    try:
        result = peter_lynch_agent(state)
        signals = state["data"]["analyst_signals"].get("peter_lynch_agent", {})
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
        test_peter_lynch(t)
