#!/usr/bin/env python
"""
验证 _synthesize_ttm_line_items_from_roic 和 _get_financial_metrics_roic_ttm 数据一致性
检查两个函数是否返回相同的最新报告期
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import (
    _get_financial_metrics_roic_ttm,
    _synthesize_ttm_line_items_from_roic,
)

def test_consistency(ticker="AAPL", end_date="2026-07-24"):
    print(f"测试 {ticker}, end_date={end_date}")
    
    # 获取财务指标
    metrics = _get_financial_metrics_roic_ttm(ticker, end_date, limit=5)
    if not metrics:
        print("❌ 财务指标为空")
        return
    
    # 获取行项目
    line_items = _synthesize_ttm_line_items_from_roic(ticker, end_date, limit=5)
    if not line_items:
        print("❌ 行项目为空")
        return
    
    # 取最新报告期
    latest_metric_date = metrics[0].report_period
    latest_item_date = line_items[0].report_period
    
    print(f"财务指标最新报告期: {latest_metric_date}")
    print(f"行项目最新报告期: {latest_item_date}")
    
    if latest_metric_date == latest_item_date:
        print("✅ 报告期一致，数据同步。")
    else:
        print(f"❌ 报告期不一致！财务指标: {latest_metric_date}, 行项目: {latest_item_date}")
        print("   --> 推测缓存键不同导致数据不同步。")

if __name__ == "__main__":
    # 测试 AAPL 和 MSFT
    test_consistency("AAPL", "2026-07-24")
    test_consistency("MSFT", "2026-07-24")
