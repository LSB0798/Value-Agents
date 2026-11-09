#!/usr/bin/env python
"""
测试 Finnhub API 获取历史 P/E 数据（使用 requests 避免超时）
"""

import os
import requests
import json
from pprint import pprint

API_KEY = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
TICKER = "AAPL"

def test_finnhub_pe():
    print(f"🔍 获取 {TICKER} 的基本财务指标...")
    
    url = f"https://finnhub.io/api/v1/stock/metric?symbol={TICKER}&metric=all&token={API_KEY}"
    
    try:
        response = requests.get(url, timeout=30)  # 30秒超时
        response.raise_for_status()
        res = response.json()
        
        print("\n📋 返回的顶层键:", list(res.keys()))
        
        if 'series' in res:
            series = res['series']
            print("\n📈 历史序列 (series) 的键:", list(series.keys()))
            
            # 检查 'annual' 序列
            if 'annual' in series:
                annual = series['annual']
                print(f"\n📅 annual 的类型: {type(annual)}")
                if isinstance(annual, dict):
                    print(f"📅 annual 的键（年份）: {list(annual.keys())}")
                    first_key = list(annual.keys())[0]
                    print(f"📅 第一个键: {first_key}")
                    first_value = annual[first_key]
                    print(f"📅 对应值的类型: {type(first_value)}")
                    print(f"📅 对应值的内容: {first_value}")
                    if isinstance(first_value, dict):
                        pe = first_value.get('pe')
                        print(f"📅 该年份的 PE: {pe}")
                else:
                    print("annual 不是字典")
            
            # 检查 'quarterly'
            if 'quarterly' in series:
                quarterly = series['quarterly']
                print(f"\n📅 quarterly 的类型: {type(quarterly)}")
                if isinstance(quarterly, dict):
                    print(f"📅 quarterly 的键（日期）: {list(quarterly.keys())}")
        else:
            print("\n⚠️ 未找到 'series' 字段")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时，请检查网络或增加超时时间")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    test_finnhub_pe()