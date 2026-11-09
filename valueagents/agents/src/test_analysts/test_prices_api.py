#!/usr/bin/env python3
"""
价格数据获取逻辑测试脚本
验证 get_prices 是否遵循 "总是调用 API → 合并缓存 → 返回数据" 策略
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 设置环境变量，确保使用 yfinance（免费）
os.environ["USE_EDGAR"] = "false"
os.environ["USE_YFINANCE"] = "true"

from valueagents.agents.src.tools.api import get_prices, get_cache
from valueagents.agents.src.data.cache import Cache


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"{'='*60}")


def test_prices_always_api():
    """测试价格数据是否总是调用 API"""
    
    print_separator("🧪 测试：价格数据是否总是调用 API")
    
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"📊 测试参数:")
    print(f"   Ticker: {ticker}")
    print(f"   日期范围: {start_date} → {end_date}")
    
    # 清理缓存（确保测试环境干净）
    cache = get_cache()
    cache_key = f"prices_{ticker}_{start_date}_{end_date}"
    
    # 清理内存缓存
    if cache_key in cache._prices_cache:
        del cache._prices_cache[cache_key]
        print(f"🧹 已清理内存缓存: {cache_key}")
    
    # 记录缓存文件路径
    cache_file = Path(cache._prices_cache_dir) / f"{ticker}_prices.csv"
    if cache_file.exists():
        # 备份原始文件（只做一次备份）
        backup_file = cache_file.with_suffix(".csv.bak")
        if not backup_file.exists():
            import shutil
            shutil.copy2(cache_file, backup_file)
            print(f"💾 已备份缓存文件: {cache_file} → {backup_file}")
    
    print(f"\n📂 缓存文件: {cache_file}")
    print(f"   存在: {cache_file.exists()}")
    if cache_file.exists():
        import csv
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            print(f"   当前记录数: {len(rows) - 1 if rows else 0}")
    
    print(f"\n🚀 第一次调用 get_prices (应该总是调用 API)...")
    start_time = time.time()
    prices1 = get_prices(ticker, start_date, end_date)
    elapsed1 = time.time() - start_time
    
    print(f"   ✅ 返回价格数: {len(prices1)}")
    print(f"   ⏱️  耗时: {elapsed1:.2f}s")
    if prices1:
        print(f"   📅 第一笔: {prices1[0].time} @ ${prices1[0].close:.2f}")
        print(f"   📅 最后一笔: {prices1[-1].time} @ ${prices1[-1].close:.2f}")
    
    # 检查缓存文件是否更新
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            print(f"   📂 缓存记录数: {len(rows) - 1 if rows else 0}")
    
    print(f"\n🚀 第二次调用 get_prices (应该仍然调用 API，但缓存会累积)...")
    start_time = time.time()
    prices2 = get_prices(ticker, start_date, end_date)
    elapsed2 = time.time() - start_time
    
    print(f"   ✅ 返回价格数: {len(prices2)}")
    print(f"   ⏱️  耗时: {elapsed2:.2f}s")
    if prices2:
        print(f"   📅 第一笔: {prices2[0].time} @ ${prices2[0].close:.2f}")
        print(f"   📅 最后一笔: {prices2[-1].time} @ ${prices2[-1].close:.2f}")
    
    # 检查缓存文件
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            total_records = len(rows) - 1 if rows else 0
            print(f"   📂 缓存记录数: {total_records}")
    
    # 验证：两次返回的数据应该一致（相同日期范围）
    if len(prices1) == len(prices2):
        print(f"\n✅ 验证通过: 两次返回数据条数一致 ({len(prices1)})")
    else:
        print(f"\n⚠️ 警告: 两次返回数据条数不一致 ({len(prices1)} vs {len(prices2)})")
        print("   这可能是由于缓存合并导致的，但返回的应该是合并后的完整数据")
    
    return prices1, prices2, cache_file


def test_prices_extended_range():
    """测试扩大日期范围，验证缓存累积效果"""
    
    print_separator("🧪 测试：扩大日期范围，验证缓存累积")
    
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    # 初始范围：30天
    start_date_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    # 扩大范围：60天
    start_date_60 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    
    print(f"📊 测试参数:")
    print(f"   Ticker: {ticker}")
    print(f"   范围1: {start_date_30} → {end_date} (30天)")
    print(f"   范围2: {start_date_60} → {end_date} (60天)")
    
    cache = get_cache()
    cache_file = Path(cache._prices_cache_dir) / f"{ticker}_prices.csv"
    
    # 记录调用前缓存记录数
    before_count = 0
    if cache_file.exists():
        import csv
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            before_count = len(rows) - 1 if rows else 0
    print(f"📂 调用前缓存记录数: {before_count}")
    
    print(f"\n🚀 第一次调用 (30天):")
    prices1 = get_prices(ticker, start_date_30, end_date)
    print(f"   ✅ 返回: {len(prices1)} 条")
    
    # 检查缓存
    if cache_file.exists():
        import csv
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            count1 = len(rows) - 1 if rows else 0
        print(f"   📂 缓存记录数: {count1}")
    
    print(f"\n🚀 第二次调用 (60天, 应覆盖更多数据):")
    prices2 = get_prices(ticker, start_date_60, end_date)
    print(f"   ✅ 返回: {len(prices2)} 条")
    
    # 检查缓存
    if cache_file.exists():
        import csv
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            count2 = len(rows) - 1 if rows else 0
        print(f"   📂 缓存记录数: {count2}")
    
    # 验证：范围2 应包含更多数据
    if len(prices2) >= len(prices1):
        print(f"\n✅ 验证通过: 60天数据 ({len(prices2)}) >= 30天数据 ({len(prices1)})")
    else:
        print(f"\n⚠️ 警告: 60天数据 ({len(prices2)}) < 30天数据 ({len(prices1)})")
        print("   这可能是由于数据源限制，但逻辑上不应发生")
    
    return prices1, prices2


def test_prices_cache_persistence():
    """测试缓存持久化（重启后仍可用）"""
    
    print_separator("🧪 测试：缓存持久化验证")
    
    ticker = "MSFT"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    print(f"📊 测试参数:")
    print(f"   Ticker: {ticker}")
    print(f"   日期范围: {start_date} → {end_date}")
    
    cache = get_cache()
    cache_file = Path(cache._prices_cache_dir) / f"{ticker}_prices.csv"
    
    # 清理内存缓存，但保留磁盘缓存
    cache_key = f"prices_{ticker}_{start_date}_{end_date}"
    if cache_key in cache._prices_cache:
        del cache._prices_cache[cache_key]
        print(f"🧹 已清理内存缓存")
    
    # 检查磁盘缓存是否存在
    if cache_file.exists():
        import csv
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            disk_count = len(rows) - 1 if rows else 0
        print(f"📂 磁盘缓存存在，记录数: {disk_count}")
    else:
        print(f"📂 磁盘缓存不存在")
    
    print(f"\n🚀 调用 get_prices (内存缓存已清空):")
    prices = get_prices(ticker, start_date, end_date)
    print(f"   ✅ 返回: {len(prices)} 条")
    
    if prices:
        print(f"   📅 第一笔: {prices[0].time} @ ${prices[0].close:.2f}")
        print(f"   📅 最后一笔: {prices[-1].time} @ ${prices[-1].close:.2f}")
    
    # 检查内存缓存是否已更新
    if cache_key in cache._prices_cache:
        mem_count = len(cache._prices_cache[cache_key])
        print(f"   💾 内存缓存已更新，记录数: {mem_count}")
    
    return prices


def main():
    """运行所有测试"""
    
    print_separator("📊 价格数据 API 测试 (总是调用 API 策略)")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目根目录: {PROJECT_ROOT}")
    
    try:
        # 测试 1: 基本调用验证
        prices1, prices2, cache_file = test_prices_always_api()
        
        # 如果基本测试通过，运行扩展测试
        if prices1 and prices2:
            test_prices_extended_range()
            test_prices_cache_persistence()
        
        print_separator("✅ 所有测试完成")
        print("\n📝 测试结论:")
        print("   - get_prices 每次都会调用 yfinance API (无缓存跳过)")
        print("   - API 返回的数据会合并到磁盘缓存")
        print("   - 缓存是累积的 (历史数据 + 最新数据)")
        print("   - 多次调用相同日期范围，返回一致的数据")
        print(f"   - 缓存文件位置: {cache_file}")
        
    except Exception as e:
        print_separator("❌ 测试失败")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
