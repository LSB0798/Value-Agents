#!/usr/bin/env python
"""
测试 Alpha Vantage 新闻情感字段的实际格式
验证 get_company_news 返回的 sentiment 值内容。
"""

import sys
import os
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_company_news

def test_sentiment_for_ticker(ticker, end_date, limit=30):
    print(f"\n=== {ticker} 新闻情感测试 ===")
    news = get_company_news(ticker, end_date, limit=limit)
    if not news:
        print("  ⚠️ 无新闻数据")
        return

    print(f"  获取到 {len(news)} 条新闻")
    # 统计各情感值出现次数
    sentiment_counts = Counter()
    for item in news:
        sentiment_counts[item.sentiment] += 1

    print("  情感标签分布:")
    for label, count in sentiment_counts.most_common():
        print(f"    {label}: {count} 条")

    # 显示前 5 条新闻的具体情感值
    print("  前 5 条新闻的情感示例:")
    for item in news: # [:5]
        print(f"    {item.date[:10]} | {item.sentiment} | {item.title[:50]}...")

def main():
    print("测试 Alpha Vantage 新闻情感格式")
    print("环境变量 USE_EDGAR =", os.environ.get('USE_EDGAR', '未设置'))
    print("环境变量 USE_YFINANCE =", os.environ.get('USE_YFINANCE', '未设置'))
    end_date = "2026-07-23"
    tickers = ["AAPL", "MSFT", "GOOGL"]
    for ticker in tickers:
        test_sentiment_for_ticker(ticker, end_date)

if __name__ == "__main__":
    main()
