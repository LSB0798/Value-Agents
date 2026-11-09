import os
import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')  # 调整到你的项目路径

from valueagents.agents.src.data.cache import get_cache
import json

def test_quarter_cache():
    cache = get_cache()
    ticker = "AAPL"
    
    # 模拟一些季度数据
    sample_quarters = [
        {"date": "2025-03-31", "revenue": 100000, "net_income": 25000},
        {"date": "2025-06-30", "revenue": 102000, "net_income": 26000},
    ]
    
    # 存储
    cache.set_quarters(ticker, sample_quarters)
    print(f"Stored {len(sample_quarters)} quarters for {ticker}")
    
    # 读取
    loaded = cache.get_quarters(ticker)
    print(f"Loaded {len(loaded)} quarters:")
    for q in loaded:
        print(q)
    
    # 测试合并
    new_quarters = [
        {"date": "2025-09-30", "revenue": 105000, "net_income": 27000},
    ]
    merged = cache.merge_quarters(ticker, new_quarters, key_field="date")
    print(f"After merge: {len(merged)} quarters")
    for q in merged:
        print(q)
    
    # 检查文件是否存在
    from valueagents.default_config import DEFAULT_CONFIG
    file_path = os.path.join(DEFAULT_CONFIG["data_cache_dir"], "fundamentals", "quarterly", f"{ticker}_quarters.json")
    print(f"File path: {file_path}")
    if os.path.exists(file_path):
        print("File exists!")
        with open(file_path) as f:
            print(json.load(f))
    else:
        print("File not found.")

if __name__ == "__main__":
    test_quarter_cache()
