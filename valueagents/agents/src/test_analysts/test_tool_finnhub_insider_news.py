#!/usr/bin/env python
"""
测试 Finnhub 提供的内幕交易和公司新闻数据
用于 Charlie Munger Agent 的数据补充
"""

import os
import finnhub
from datetime import datetime, timedelta

# 使用您已有的 Finnhub API Key
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
TICKER = "AAPL"

def test_insider_trades():
    """测试获取内幕交易数据"""
    print("=" * 60)
    print("1. 测试 Finnhub 内幕交易数据")
    print("=" * 60)
    
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    
    # 获取最近一年的内幕交易（从 2026-01-01 开始）
    from_date = "2026-01-01"
    try:
        res = client.stock_insider_transactions(TICKER, from_date)
        print(f"✅ 成功获取内幕交易数据")
        print(f"返回的顶层键: {list(res.keys())}")
        
        if 'data' in res:
            data = res['data']
            print(f"总交易记录数: {len(data)}")
            if data:
                # 打印前 3 条记录
                print("\n前 3 条记录示例:")
                for i, item in enumerate(data[:3]):
                    print(f"\n--- 记录 {i+1} ---")
                    print(f"  姓名: {item.get('name')}")
                    print(f"  股份变动: {item.get('change')}")
                    print(f"  交易日期: {item.get('transactionDate')}")
                    print(f"  交易价格: {item.get('transactionPrice')}")
                    print(f"  交易代码: {item.get('transactionCode')}")
            else:
                print("无内幕交易记录")
        else:
            print("响应中没有 'data' 字段")
    except Exception as e:
        print(f"❌ 获取内幕交易失败: {e}")

def test_company_news():
    """测试获取公司新闻数据"""
    print("\n" + "=" * 60)
    print("2. 测试 Finnhub 公司新闻数据")
    print("=" * 60)
    
    client = finnhub.Client(api_key=FINNHUB_API_KEY)
    
    # 获取最近 7 天的新闻
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    try:
        res = client.company_news(TICKER, _from=start_date, to=end_date)
        print(f"✅ 成功获取公司新闻数据")
        print(f"新闻总数: {len(res)}")
        if res:
            # 打印前 2 条新闻
            print("\n前 2 条新闻示例:")
            for i, item in enumerate(res[:2]):
                print(f"\n--- 新闻 {i+1} ---")
                print(f"  标题: {item.get('headline')}")
                print(f"  来源: {item.get('source')}")
                print(f"  时间: {datetime.fromtimestamp(item.get('datetime')).strftime('%Y-%m-%d %H:%M')}")
                print(f"  摘要: {item.get('summary', '')[:150]}...")
        else:
            print("未找到新闻")
    except Exception as e:
        print(f"❌ 获取公司新闻失败: {e}")

def test_alpha_vantage_news():
    """测试 Alpha Vantage 新闻（可选）"""
    print("\n" + "=" * 60)
    print("3. 测试 Alpha Vantage 新闻数据")
    print("=" * 60)
    
    # 导入已存在的 alpha_news_data_tools
    try:
        from valueagents.agents.utils.alpha_news_data_tools import get_alpha_news
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        result = get_alpha_news.invoke({"ticker": TICKER, "start_date": start_date, "end_date": end_date})
        print(f"✅ Alpha Vantage 新闻数据获取成功")
        print(f"结果预览 (前 200 字符):\n{result[:200]}...")
    except ImportError:
        print("⚠️ 未找到 alpha_news_data_tools，跳过测试")
    except Exception as e:
        print(f"❌ Alpha Vantage 新闻获取失败: {e}")

if __name__ == "__main__":
    print(f"测试 Finnhub 数据源，Ticker: {TICKER}")
    test_insider_trades()
    test_company_news()
    test_alpha_vantage_news()
    print("\n测试完成")
