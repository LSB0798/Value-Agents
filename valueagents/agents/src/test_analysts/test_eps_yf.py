#!/usr/bin/env python
"""
测试 yfinance 回退路径中 earnings_per_share 的计算
"""

import os
import sys
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# 强制使用 yfinance 回退（模拟 EDGAR 失败）
os.environ["USE_EDGAR"] = "false"
os.environ["USE_YFINANCE"] = "true"

# 重新加载 api 模块以应用环境变量
import importlib
import valueagents.agents.src.tools.api as api
importlib.reload(api)

from valueagents.agents.src.tools.api import search_line_items
from valueagents.agents.src.data.models import LineItem

def test_eps(ticker="AAPL", end_date="2026-07-23", period="annual", limit=3):
    print(f"\n{'='*80}")
    print(f"测试 yfinance 回退路径 earnings_per_share: {ticker}")
    print(f"{'='*80}")

    # 请求包含 earnings_per_share 的字段列表
    fields = [
        "net_income",
        "outstanding_shares",
        "earnings_per_share",
    ]

    try:
        line_items = search_line_items(ticker, fields, end_date, period=period, limit=limit)
        if not line_items:
            print("❌ 未获取到任何行项目")
            return

        print(f"✅ 获取到 {len(line_items)} 条记录")
        latest = line_items[0]
        print("最新记录字段检查:")
        for field in fields:
            value = getattr(latest, field, None)
            print(f"  {field:>20}: {value}")

        # 验证 earnings_per_share 是否等于 net_income / outstanding_shares
        if latest.net_income and latest.outstanding_shares and latest.earnings_per_share:
            expected_eps = latest.net_income / latest.outstanding_shares
            actual_eps = latest.earnings_per_share
            if abs(actual_eps - expected_eps) < 1e-6:
                print("✅ earnings_per_share 计算正确")
            else:
                print(f"⚠️ earnings_per_share 可能不正确: expected {expected_eps:.4f}, got {actual_eps:.4f}")
        else:
            if latest.earnings_per_share is None:
                print("⚠️ earnings_per_share 为 None，可能数据不足")
            else:
                print("⚠️ 无法验证 earnings_per_share（缺失 net_income 或 outstanding_shares）")

    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    for ticker in ["AAPL", "MSFT", "GOOGL", "TSLA"]:
        test_eps(ticker)
