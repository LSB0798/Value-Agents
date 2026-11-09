#!/usr/bin/env python
"""
全面测试 growth_analyst_agent
"""

import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.analysts.growth_agent import growth_analyst_agent

def test_growth_agent(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 growth_analyst_agent: {ticker}")
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
        result = growth_analyst_agent(state)
        signals = state["data"]["analyst_signals"].get("growth_analyst_agent", {})
        if signals and ticker in signals:
            sig = signals[ticker]
            print(f"信号: {sig['signal']}")
            print(f"置信度: {sig['confidence']}")
            reasoning = sig.get('reasoning', {})
            print("推理细节:")
            pprint(reasoning)
            # 检查关键子分数
            print("\n子分数:")
            for key in ['historical_growth', 'growth_valuation', 'margin_expansion', 'insider_conviction', 'financial_health']:
                if key in reasoning:
                    print(f"  {key}: score={reasoning[key].get('score', 'N/A')}")
            if 'final_analysis' in reasoning:
                fa = reasoning['final_analysis']
                print(f"  加权得分: {fa.get('weighted_score', 'N/A')}")
        else:
            print("❌ 未生成信号")
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_growth_agent(t)
