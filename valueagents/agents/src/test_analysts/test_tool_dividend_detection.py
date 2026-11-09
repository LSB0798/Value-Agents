#!/usr/bin/env python
"""
测试 Ben Graham Agent 对分红数据的检测
通过 mock search_line_items 强制返回大额分红数据
"""

import os
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"

import sys
import json
from unittest.mock import patch, MagicMock
from valueagents.agents.src.analysts.ben_graham import ben_graham_agent
from valueagents.agents.src.data.models import LineItem

def create_mock_line_items():
    """创建模拟的 LineItem 对象，包含大额分红数据"""
    # 构建一个 LineItem 字典，包含所有 ben_graham 需要的字段
    # 我们只关心分红，其他字段设为合理值
    mock_items = []
    years = [2025, 2024, 2023, 2022, 2021]
    for yr in years:
        item = LineItem(
            ticker="AAPL",
            report_period=f"{yr}-12-31",
            period="annual",
            currency="USD",
            earnings_per_share=7.0,
            revenue=400000000000,
            net_income=100000000000,
            book_value_per_share=5.0,
            total_assets=350000000000,
            total_liabilities=250000000000,
            current_assets=150000000000,
            current_liabilities=130000000000,
            dividends_and_other_cash_distributions=15421000000.0,  # 大额正分红
            outstanding_shares=15000000000,
        )
        mock_items.append(item)
    return mock_items

def test_with_mock_dividend():
    """使用 mock 数据测试分红检测"""
    # 原始 state
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

    # 我们需要 mock search_line_items 函数
    # 但由于 search_line_items 在 api.py 中，且 ben_graham 通过 from valueagents.agents.src.tools.api import search_line_items
    # 我们可以 mock valueagents.agents.src.tools.api.search_line_items
    with patch('valueagents.agents.src.tools.api.search_line_items') as mock_search:
        # 设置返回值
        mock_search.return_value = create_mock_line_items()
        
        # 同时还需要 mock get_financial_metrics 和 get_market_cap 以避免网络调用
        # 但我们希望尽量接近真实，只替换关键部分
        # 更全面的 mock，但为了简单，我们可以 patch 整个 api 的 get 函数
        # 但我们的重点是分红，所以只 mock search_line_items
        
        # 调用 agent
        result = ben_graham_agent(state, agent_id="ben_graham_agent")
        
        # 获取信号
        signals = state["data"]["analyst_signals"].get("ben_graham_agent", {})
        for ticker, sig in signals.items():
            print(f"\nSignal: {sig.get('signal')}")
            print(f"Confidence: {sig.get('confidence')}")
            print(f"Reasoning:\n{sig.get('reasoning')}")
            # 检查是否提到分红
            if "dividend" in sig.get('reasoning', '').lower():
                print("\n✅ 分红被提及 (可能已识别)")
            else:
                print("\n❌ 分红未被提及 (可能未识别)")

if __name__ == "__main__":
    test_with_mock_dividend()
