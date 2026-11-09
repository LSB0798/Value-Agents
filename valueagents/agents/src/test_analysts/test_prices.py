# test_prices.py
import os
import sys
import pandas as pd
from valueagents.agents.src.tools.api import get_prices
from valueagents.agents.src.data.cache import get_cache
from valueagents.default_config import DEFAULT_CONFIG

def test_prices():
    ticker = "AAPL"
    start_date = "2026-07-01"
    end_date = "2026-07-31"

    print("=== 测试价格数据获取 (总是调用API) ===")
    print(f"获取 {ticker} 从 {start_date} 到 {end_date} 的价格数据...\n")

    # 第一次调用
    prices1 = get_prices(ticker, start_date, end_date)
    print(f"✅ 第一次调用返回 {len(prices1)} 条记录")

    # 查看缓存文件是否存在
    cache = get_cache()
    file_path = os.path.join(
        DEFAULT_CONFIG["data_cache_dir"],
        "prices", "daily", f"{ticker}_prices.csv"
    )
    
    if os.path.exists(file_path):
        df1 = pd.read_csv(file_path)
        print(f"📁 缓存文件存在: {file_path}")
        print(f"   缓存文件中共有 {len(df1)} 条记录")
    else:
        print("⚠️ 缓存文件尚未创建（可能本次未写入）")
        df1 = None

    # 第二次调用（应再次调用API，而非从缓存读取）
    prices2 = get_prices(ticker, start_date, end_date)
    print(f"\n✅ 第二次调用返回 {len(prices2)} 条记录")

    # 比较两次调用结果
    if len(prices1) == len(prices2):
        print("   (两次调用返回的记录数相同)")
    else:
        print(f"   (记录数不同: 第一次 {len(prices1)}, 第二次 {len(prices2)})")

    # 检查缓存文件更新
    if os.path.exists(file_path):
        df2 = pd.read_csv(file_path)
        print(f"\n📁 缓存文件现在有 {len(df2)} 条记录")
        if df1 is not None and len(df2) >= len(df1):
            print("   ✅ 缓存已正确累积（记录数未减少）")
        else:
            print("   ⚠️ 缓存记录数可能异常")

    # 打印前几条记录（仅当有数据时）
    if prices1:
        print("\n📋 前3条记录示例:")
        for p in prices1[:3]:
            print(f"   {p.time}  O:{p.open:.2f}  H:{p.high:.2f}  L:{p.low:.2f}  C:{p.close:.2f}  V:{p.volume}")

if __name__ == "__main__":
    test_prices()
