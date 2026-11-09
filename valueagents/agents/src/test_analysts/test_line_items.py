# test_line_items.py
import os
import sys
import json
from valueagents.agents.src.tools.api import search_line_items
from valueagents.agents.src.data.cache import get_cache
from valueagents.default_config import DEFAULT_CONFIG

def test_line_items():
    ticker = "AAPL"
    end_date = "2026-07-31"
    period = "ttm"           # 可改为 "annual"
    line_items = ["revenue", "net_income", "free_cash_flow", "ebit", "total_debt"]
    limit = 3

    print("=== 测试行项目数据获取 (总是调用API) ===")
    print(f"获取 {ticker} 截至 {end_date} 的行项目 ({period})，字段: {line_items}，limit: {limit}\n")

    # 第一次调用
    items1 = search_line_items(ticker, line_items, end_date, period, limit)
    print(f"✅ 第一次调用返回 {len(items1)} 条记录")
    if items1:
        print("   示例记录 (最新):")
        item = items1[0]
        print(f"   报告期: {item.report_period}")
        for f in line_items:
            val = getattr(item, f, None)
            print(f"      {f}: {val}")

    # 查看缓存文件
    cache = get_cache()
    cache_file = os.path.join(
        DEFAULT_CONFIG["data_cache_dir"],
        "line_items",
        f"{ticker}_{period}_line_items.json"
    )
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_records = json.load(f)
        print(f"\n📁 缓存文件存在: {cache_file}")
        print(f"   缓存文件中总共有 {len(cached_records)} 条记录")
        # 显示最近3条的报告期
        if cached_records:
            recent = sorted(cached_records, key=lambda x: x.get('report_period', ''), reverse=True)[:3]
            print("   最近3条报告期:", [r['report_period'] for r in recent])
    else:
        print("\n⚠️ 缓存文件尚未创建")

    # 第二次调用
    items2 = search_line_items(ticker, line_items, end_date, period, limit)
    print(f"\n✅ 第二次调用返回 {len(items2)} 条记录")
    if items2:
        print("   示例记录 (最新):")
        item = items2[0]
        print(f"   报告期: {item.report_period}")
        for f in line_items:
            val = getattr(item, f, None)
            print(f"      {f}: {val}")

    # 比较记录数
    print(f"\n📊 两次返回记录数相同: {len(items1) == len(items2)}")

    # 再次检查缓存文件
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_records2 = json.load(f)
        print(f"\n📁 缓存文件现在有 {len(cached_records2)} 条记录")
        if len(cached_records2) >= len(cached_records):
            print("   ✅ 缓存已正确累积（记录数未减少）")
        else:
            print("   ⚠️ 缓存记录数可能异常")

if __name__ == "__main__":
    test_line_items()
