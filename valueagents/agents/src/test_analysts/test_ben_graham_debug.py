#!/usr/bin/env python
"""
测试 Ben Graham Agent，打印详细的中间数据
"""

import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import json
from pprint import pprint
from valueagents.agents.src.analysts.ben_graham import ben_graham_agent

def test_ben_graham():
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

    print("🔍 测试 Ben Graham Agent (EDGAR 模式)")
    print(f"   Ticker: {state['data']['tickers'][0]}, End Date: {state['data']['end_date']}\n")

    # 调用 agent
    result = ben_graham_agent(state, agent_id="ben_graham_agent")

    # 获取 signals
    signals = state["data"]["analyst_signals"].get("ben_graham_agent", {})
    
    print("\n" + "="*60)
    print("📊 Ben Graham Signal")
    print("="*60)
    for ticker, sig in signals.items():
        print(f"  Ticker: {ticker}")
        print(f"  Signal: {sig.get('signal')}")
        print(f"  Confidence: {sig.get('confidence')}")
        print(f"  Reasoning:\n{sig.get('reasoning')}")

    # 可选：打印 LineItem 数据（用于调试）
    # 注意：line_items 可能不在 state 中，但我们可以从 agent 内部获取，这里忽略

if __name__ == "__main__":
    test_ben_graham()
