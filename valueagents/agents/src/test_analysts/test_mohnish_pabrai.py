#!/usr/bin/env python
"""
测试 mohnish_pabrai_agent 的性能
"""

import sys
import os
import json
import re
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.analysts.mohnish_pabrai import mohnish_pabrai_agent

def parse_reasoning_for_metrics(reasoning: str) -> dict:
    """从推理文本中提取关键数值（FCF yield, 下行保护, 翻倍潜力）"""
    metrics = {"fcf_yield": None, "downside_score": None, "double_potential": None}
    # 提取 FCF yield
    fcf_match = re.search(r'FCF yield (\d+\.?\d*)%', reasoning)
    if fcf_match:
        metrics["fcf_yield"] = float(fcf_match.group(1))
    # 提取 downside score（可能以 "Downside score X/10" 形式）
    down_match = re.search(r'downside[:\s]*(\d+\.?\d*)/10', reasoning, re.IGNORECASE)
    if down_match:
        metrics["downside_score"] = float(down_match.group(1))
    # 提取 double potential
    double_match = re.search(r'double[:\s]*(\d+\.?\d*)/10', reasoning, re.IGNORECASE)
    if double_match:
        metrics["double_potential"] = float(double_match.group(1))
    return metrics

def test_pabrai(ticker, end_date="2026-07-23"):
    print(f"\n{'='*80}")
    print(f"测试 mohnish_pabrai_agent: {ticker}")
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
        result = mohnish_pabrai_agent(state)
        signals = state["data"]["analyst_signals"].get("mohnish_pabrai_agent", {})
        if signals and ticker in signals:
            sig = signals[ticker]
            print(f"信号: {sig['signal']}")
            print(f"置信度: {sig['confidence']}")
            print("推理文本:")
            print(sig['reasoning'])
            # 解析数值
            parsed = parse_reasoning_for_metrics(sig['reasoning'])
            print("\n解析到的关键数值:")
            for k, v in parsed.items():
                print(f"  {k}: {v}")
        else:
            print("❌ 未生成信号")
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    for t in tickers:
        test_pabrai(t)
