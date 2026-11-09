#!/usr/bin/env python
"""
测试 Nassim Taleb Agent 在 EDGAR 模式下的数据获取和分析
"""

import os
# 必须在导入任何 valueagents 模块之前设置环境变量
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import json
from valueagents.agents.src.analysts.nassim_taleb import nassim_taleb_agent

def test_nassim_taleb():
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

    print("🔍 测试 Nassim Taleb Agent (EDGAR 模式)")
    print(f"   Ticker: {state['data']['tickers'][0]}, End Date: {state['data']['end_date']}")

    # 调用 agent
    result = nassim_taleb_agent(state, agent_id="nassim_taleb_agent")

    # 打印结果
    print("\n=== Agent Output ===")
    print("Messages:", result.get("messages"))

    # 从 state 中获取信号
    signals = state["data"]["analyst_signals"].get("nassim_taleb_agent", {})
    print("\n📊 Nassim Taleb Signal:")
    for ticker, sig in signals.items():
        print(f"  {ticker}: {sig.get('signal')} (confidence: {sig.get('confidence')})")
        print(f"  Reasoning: {sig.get('reasoning')}")

if __name__ == "__main__":
    test_nassim_taleb()
