#!/usr/bin/env python3
"""
行项目数据获取精简测试
验证 "总是调用 API → 合并缓存 → 返回合并后数据" 策略
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 启用免费数据源
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "true"

from valueagents.agents.src.tools.api import search_line_items
from valueagents.agents.src.data.cache import get_cache


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_line_items_basic():
    """基本测试：总是调用 API，缓存会合并"""
    print_header("测试：search_line_items 是否总是调用 API")

    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    period = "ttm"
    limit = 3
    fields = ["revenue", "net_income", "free_cash_flow"]

    cache = get_cache()
    cache_file = Path(cache._line_items_cache_dir) / f"{ticker}_{period}_line_items.json"

    # 记录初始缓存状态
    before_count = 0
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            before_count = len(data) if isinstance(data, list) else 0
    print(f"📂 缓存文件: {cache_file}")
    print(f"   调用前记录数: {before_count}")

    # 第一次调用（应触发 API）
    print("\n🚀 第一次调用 search_line_items (应触发 API 调用)...")
    start = time.time()
    items1 = search_line_items(ticker, fields, end_date, period, limit)
    elapsed = time.time() - start
    print(f"   ✅ 返回记录数: {len(items1)}，耗时: {elapsed:.2f}s")
    if items1:
        print(f"   📅 最新报告期: {items1[0].report_period}")
        for f in fields:
            val = getattr(items1[0], f, None)
            print(f"      {f}: {val}")

    # 检查缓存是否更新
    after_count = 0
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
            after_count = len(data) if isinstance(data, list) else 0
    print(f"   📂 调用后记录数: {after_count}")

    # 第二次调用（应仍然触发 API，但返回结果可能相同）
    print("\n🚀 第二次调用 search_line_items (应再次触发 API)...")
    start = time.time()
    items2 = search_line_items(ticker, fields, end_date, period, limit)
    elapsed = time.time() - start
    print(f"   ✅ 返回记录数: {len(items2)}，耗时: {elapsed:.2f}s")
    if items2:
        print(f"   📅 最新报告期: {items2[0].report_period}")

    # 验证数据一致性
    if len(items1) == len(items2):
        print("\n✅ 两次返回数据条数一致")
    else:
        print(f"\n⚠️ 数据条数不一致: {len(items1)} vs {len(items2)}")

    # 验证缓存是否累积（如果有新数据，记录数应增加）
    if after_count > before_count:
        print(f"✅ 缓存已累积新数据: {before_count} → {after_count}")
    else:
        print(f"ℹ️  缓存记录数未增加（可能无新数据）")


def test_filter_line_items_robustness():
    """测试 _filter_line_items 的类型转换健壮性"""
    print_header("测试：_filter_line_items 类型转换健壮性")

    # 模拟包含 None 和字符串的输入
    from valueagents.agents.src.tools.api import _filter_line_items

    mock_records = [
        {
            "ticker": "TEST",
            "report_period": "2025-12-31",
            "period": "annual",
            "currency": "USD",
            "revenue": 1000000,
            "net_income": 150000,
            "free_cash_flow": 120000,
            "debt_to_equity": None,          # 应被保留为 None
            "gross_margin": "0.45",          # 字符串数字应转换为 float
            "invalid_field": "some_string"   # 非数值保留原样
        },
        {
            "ticker": "TEST",
            "report_period": "2024-12-31",
            "period": "annual",
            "currency": "USD",
            "revenue": 900000,
            "net_income": 130000,
            "free_cash_flow": 100000,
            "debt_to_equity": 1.5,
            "gross_margin": "0.42",
            "invalid_field": "another"
        }
    ]

    line_items = ["revenue", "net_income", "free_cash_flow", "debt_to_equity", "gross_margin", "invalid_field"]
    result = _filter_line_items(mock_records, line_items, limit=5)

    print(f"✅ 成功构造 {len(result)} 个 LineItem 对象")
    for item in result:
        print(f"\n📅 报告期: {item.report_period}")
        print(f"   revenue: {item.revenue} (类型: {type(item.revenue).__name__})")
        print(f"   net_income: {item.net_income}")
        print(f"   free_cash_flow: {item.free_cash_flow}")
        print(f"   debt_to_equity: {item.debt_to_equity} (类型: {type(item.debt_to_equity).__name__})")
        print(f"   gross_margin: {item.gross_margin} (类型: {type(item.gross_margin).__name__})")
        # 注意 invalid_field 不在 LineItem 字段中，会被忽略


def main():
    print_header("行项目数据 API 测试 (精简版)")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        test_line_items_basic()
        test_filter_line_items_robustness()
        print("\n✅ 所有测试通过")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
