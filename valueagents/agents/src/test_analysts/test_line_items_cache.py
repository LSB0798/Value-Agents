#!/usr/bin/env python
"""
全面测试 search_line_items 磁盘持久化缓存。

测试内容：
1. 首次调用（缓存未命中）从数据源获取，并写入缓存文件。
2. 第二次调用（缓存命中）从磁盘读取，不再调用底层数据源。
3. 验证返回的 LineItem 对象包含所有请求字段，特别是 ebit。
4. 验证不同字段组合能正确过滤，并且都能命中缓存。
5. 验证缓存文件内容完整。
"""

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = "/data/lishuaibing/valueagents/ValueAgents"
sys.path.insert(0, PROJECT_ROOT)

# 设置环境变量（确保 EDGAR 和 yfinance 可用）
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "true"
os.environ["FINANCIAL_DATASETS_API_KEY"] = "7822668c-eb7d-43b6-bee4-fb31a46e182a"

from valueagents.agents.src.tools.api import search_line_items
from valueagents.agents.src.data.cache import get_cache
from valueagents.default_config import DEFAULT_CONFIG

TICKER = "AAPL"
PERIOD = "annual"       # 或 "ttm"
END_DATE = "2025-12-31"
LIMIT = 5

# 两组不同的字段组合
FIELDS_GROUP1 = ["revenue", "net_income", "free_cash_flow", "total_debt", "outstanding_shares"]
FIELDS_GROUP2 = ["revenue", "net_income", "ebit", "ebitda", "free_cash_flow"]  # 包含 ebit

def clear_cache(ticker, period):
    """删除该 ticker 和 period 的缓存文件，确保测试独立。"""
    cache_dir = Path(DEFAULT_CONFIG["data_cache_dir"]) / "line_items"
    cache_file = cache_dir / f"{ticker}_{period}_line_items.json"
    if cache_file.exists():
        cache_file.unlink()
        print(f"[Test] Removed cache file: {cache_file}")
    else:
        print(f"[Test] No cache file to remove: {cache_file}")

def test_search(ticker, period, end_date, fields, limit, call_description):
    """执行一次 search_line_items 并打印结果摘要。"""
    print(f"\n--- {call_description} ---")
    print(f"Requested fields: {fields}")
    result = search_line_items(
        ticker=ticker,
        line_items=fields,
        end_date=end_date,
        period=period,
        limit=limit
    )
    print(f"Received {len(result)} items.")
    if result:
        # 打印第一条记录的所有请求字段（加上 report_period）
        first = result[0]
        print("First item fields:")
        print(f"  report_period: {first.report_period}")
        for f in fields:
            val = getattr(first, f, None)
            print(f"  {f}: {val}")
    return result

def main():
    print("=" * 70)
    print("Testing search_line_items with disk caching (full validation)")
    print("=" * 70)
    
    # 1. 清理缓存，确保首次调用从数据源获取
    clear_cache(TICKER, PERIOD)
    
    # 2. 第一次调用（组1）：应触发数据获取并写入缓存
    result1 = test_search(TICKER, PERIOD, END_DATE, FIELDS_GROUP1, LIMIT, 
                          "First call (should fetch from data source) - Group1")
    
    # 3. 第二次调用（组1）：应命中缓存
    result2 = test_search(TICKER, PERIOD, END_DATE, FIELDS_GROUP1, LIMIT,
                          "Second call (should hit cache) - Group1")
    
    # 4. 第三次调用（组2）：应命中缓存（因为缓存是完整记录，不同字段组合可复用）
    result3 = test_search(TICKER, PERIOD, END_DATE, FIELDS_GROUP2, LIMIT,
                          "Third call (different fields, should still hit cache) - Group2")
    
    # 5. 验证缓存文件存在且包含完整记录
    cache_dir = Path(DEFAULT_CONFIG["data_cache_dir"]) / "line_items"
    cache_file = cache_dir / f"{TICKER}_{PERIOD}_line_items.json"
    print(f"\n[Test] Cache file path: {cache_file}")
    if cache_file.exists():
        print("[Test] Cache file exists.")
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
            print(f"[Test] Cached records count: {len(cached_data)}")
            if cached_data:
                # 显示第一条记录的所有键（字段）
                sample = cached_data[0]
                print("Sample cached record keys:")
                print("  " + ", ".join(sample.keys()))
                # 确认 ebit 和 ebitda 在缓存中（即使组1没请求，也应存在）
                if 'ebit' in sample and 'ebitda' in sample:
                    print("[Test] Cache contains 'ebit' and 'ebitda' fields (full record).")
                else:
                    print("[Test] WARNING: Cache may not contain full fields.")
    else:
        print("[Test] Cache file NOT found - caching failed!")
    
    # 6. 验证结果的一致性
    print("\n[Test] Validation results:")
    if len(result1) == len(result2) == len(result3):
        print("  All calls returned same number of items (OK).")
    else:
        print(f"  Count mismatch: r1={len(result1)}, r2={len(result2)}, r3={len(result3)} (FAIL)")

    # 检查组2的返回是否包含 ebit
    if result3 and hasattr(result3[0], 'ebit'):
        ebit_val = getattr(result3[0], 'ebit')
        print(f"  Third call includes 'ebit' field: {ebit_val} (OK).")
    else:
        print("  Third call did NOT include 'ebit' (FAIL).")

    # 检查组2的 ebit 是否与缓存中的一致（简单比较）
    if result3 and cached_data:
        # 从缓存中找对应 report_period 的记录
        rp = result3[0].report_period
        cache_item = next((item for item in cached_data if item.get('report_period') == rp), None)
        if cache_item and 'ebit' in cache_item:
            if abs(cache_item['ebit'] - result3[0].ebit) < 1e-6:
                print("  'ebit' value matches cache (OK).")
            else:
                print("  'ebit' value mismatch (FAIL).")
        else:
            print("  Cache does not contain 'ebit' for this period (FAIL).")
    
    print("\n[Test] Done.")

if __name__ == "__main__":
    main()
