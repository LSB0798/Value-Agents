#!/usr/bin/env python
"""
测试 Finnhub API 获取历史 P/E 数据
"""

import os
import finnhub
import json
from pprint import pprint

API_KEY = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
TICKER = "AAPL"

def test_finnhub_pe():
    client = finnhub.Client(api_key=API_KEY)
    print(f"🔍 获取 {TICKER} 的基本财务指标...")
    
    try:
        res = client.company_basic_financials(TICKER, 'all')
        print("\n📋 返回的顶层键:", list(res.keys()))
        
        if 'series' in res:
            series = res['series']
            print("\n📈 历史序列 (series) 的键:", list(series.keys()))
            
            # 检查 'annual' 序列
            if 'annual' in series:
                annual = series['annual']
                print(f"\n📅 annual 的类型: {type(annual)}")
                print(f"📅 annual 的长度: {len(annual) if hasattr(annual, '__len__') else 'N/A'}")
                if isinstance(annual, list) and annual:
                    first = annual[0]
                    print(f"📅 annual 第一个元素的类型: {type(first)}")
                    print(f"📅 annual 第一个元素的内容（前200字符）: {str(first)[:200]}")
                    # 如果第一个元素是字符串，尝试解析 JSON
                    if isinstance(first, str):
                        try:
                            parsed = json.loads(first)
                            print(f"解析为 JSON 后: {parsed}")
                            print(f"  period: {parsed.get('period')}")
                            print(f"  v.pe: {parsed.get('v', {}).get('pe')}")
                        except json.JSONDecodeError:
                            print("无法解析为 JSON")
                else:
                    print("annual 不是列表或为空")
            
            # 检查 'quarterly'
            if 'quarterly' in series:
                quarterly = series['quarterly']
                print(f"\n📅 quarterly 的类型: {type(quarterly)}")
                if isinstance(quarterly, list) and quarterly:
                    first = quarterly[0]
                    print(f"📅 quarterly 第一个元素的类型: {type(first)}")
                    print(f"📅 quarterly 第一个元素的内容: {str(first)[:200]}")
                    if isinstance(first, str):
                        try:
                            parsed = json.loads(first)
                            print(f"解析为 JSON 后: {parsed}")
                        except json.JSONDecodeError:
                            print("无法解析为 JSON")
        else:
            print("\n⚠️ 未找到 'series' 字段")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_finnhub_pe()