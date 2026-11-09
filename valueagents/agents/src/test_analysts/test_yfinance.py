#!/usr/bin/env python
"""
测试 yfinance 是否可用
"""

import yfinance as yf
import time

def test_yfinance():
    print("测试 yfinance 连接...")
    ticker = "AAPL"
    try:
        stock = yf.Ticker(ticker)
        print(f"获取 {ticker} 的 info...")
        info = stock.info
        print(f"✅ 成功获取 info，键数: {len(info)}")
        print(f"  当前价格: {info.get('regularMarketPrice', info.get('currentPrice', 'N/A'))}")
        print(f"  市值: {info.get('marketCap', 'N/A')}")
        print(f"  市盈率: {info.get('trailingPE', 'N/A')}")
        print(f"  Beta: {info.get('beta', 'N/A')}")
        
        # 测试历史数据
        print(f"\n获取 {ticker} 的历史数据（最近5天）...")
        hist = stock.history(period="5d")
        if not hist.empty:
            print(f"✅ 成功获取历史数据，共 {len(hist)} 条记录")
            print(hist[['Open', 'Close']].tail())
        else:
            print("⚠️  历史数据为空")
            
    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    test_yfinance()
