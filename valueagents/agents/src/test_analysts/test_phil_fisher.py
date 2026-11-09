#!/usr/bin/env python
"""
测试 Phil Fisher Agent 在 EDGAR 模式下的数据获取和分析
"""

import os
# 必须在导入任何 valueagents 模块之前设置环境变量
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import json
from valueagents.agents.src.analysts.phil_fisher import phil_fisher_agent

def test_phil_fisher():
    # 构造最小状态
    state = {
        "data": {
            "tickers": ["AAPL"],
            "end_date": "2026-07-10",
            "start_date": "2025-07-10",
            "analyst_signals": {},
        },
        "metadata": {
            "show_reasoning": True,
        }
    }

    print("🔍 测试 Phil Fisher Agent (EDGAR 模式)")
    print(f"   Ticker: {state['data']['tickers'][0]}, End Date: {state['data']['end_date']}")

    # 调用 agent
    result = phil_fisher_agent(state, agent_id="phil_fisher_agent")

    # 打印结果
    print("\n=== Agent Output ===")
    print("Messages:", result.get("messages"))

    # 从 state 中获取信号
    signals = state["data"]["analyst_signals"].get("phil_fisher_agent", {})
    print("\n📊 Phil Fisher Signal:")
    for ticker, sig in signals.items():
        print(f"  {ticker}: {sig.get('signal')} (confidence: {sig.get('confidence')})")
        print(f"  Reasoning: {sig.get('reasoning')}")

if __name__ == "__main__":
    test_phil_fisher()
