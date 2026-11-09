#!/usr/bin/env python
"""
测试 sentiment_analyst_agent 的数据获取和信号合成逻辑
验证 get_insider_trades 和 get_company_news 在现有配置下的行为
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_insider_trades, get_company_news

def test_sentiment_for_ticker(ticker, end_date):
    """模拟 sentiment_analyst_agent 的核心逻辑，打印分析结果"""
    print(f"\n=== 测试 {ticker} ===")
    
    # 1. 获取内幕交易
    print("\n--- 内幕交易 ---")
    insider_trades = get_insider_trades(ticker, end_date, limit=1000)
    if not insider_trades:
        print("⚠️  无内幕交易数据")
        insider_signals = []
    else:
        # 提取交易股数（正=买入，负=卖出）
        transaction_shares = pd.Series([t.transaction_shares for t in insider_trades]).dropna()
        insider_signals = np.where(transaction_shares < 0, "bearish", "bullish").tolist()
        print(f"✅ 获取到 {len(insider_trades)} 条内幕交易记录")
        print(f"   看涨: {insider_signals.count('bullish')}, 看跌: {insider_signals.count('bearish')}")
        # 展示最近几条（使用正确的字段名）
        for trade in insider_trades[:3]:
            price = trade.transaction_price_per_share or 0
            print(f"   {trade.name} | {trade.transaction_date} | shares={trade.transaction_shares} | price={price:.2f}")
    
    # 2. 获取公司新闻
    print("\n--- 公司新闻 ---")
    company_news = get_company_news(ticker, end_date, limit=100)
    if not company_news:
        print("⚠️  无新闻数据")
        news_signals = []
    else:
        # 提取情感标签（仅保留有情感值的）
        sentiment_list = [n.sentiment for n in company_news if n.sentiment is not None]
        news_signals = np.where(pd.Series(sentiment_list) == "negative", "bearish",
                               np.where(pd.Series(sentiment_list) == "positive", "bullish", "neutral")).tolist()
        print(f"✅ 获取到 {len(company_news)} 条新闻")
        print(f"   有情感标签的: {len(sentiment_list)} 条")
        print(f"   看涨: {news_signals.count('bullish')}, 看跌: {news_signals.count('bearish')}, 中性: {news_signals.count('neutral')}")
        # 展示前两条新闻
        for news in company_news[:2]:
            print(f"   {news.date} | {news.title[:60]}... | sentiment={news.sentiment}")
    
    # 3. 合成信号（与 sentiment.py 逻辑一致）
    insider_weight = 0.3
    news_weight = 0.7
    
    bullish_signals = (
        insider_signals.count("bullish") * insider_weight +
        news_signals.count("bullish") * news_weight
    )
    bearish_signals = (
        insider_signals.count("bearish") * insider_weight +
        news_signals.count("bearish") * news_weight
    )
    
    total_weighted_signals = len(insider_signals) * insider_weight + len(news_signals) * news_weight
    if total_weighted_signals > 0:
        confidence = round((max(bullish_signals, bearish_signals) / total_weighted_signals) * 100, 2)
    else:
        confidence = 0.0
    
    if bullish_signals > bearish_signals:
        overall_signal = "bullish"
    elif bearish_signals > bullish_signals:
        overall_signal = "bearish"
    else:
        overall_signal = "neutral"
    
    print(f"\n--- 最终信号 ---")
    print(f"信号: {overall_signal}")
    print(f"置信度: {confidence:.1f}%")
    print(f"加权看涨: {bullish_signals:.1f}, 加权看跌: {bearish_signals:.1f}")
    
    return {
        "signal": overall_signal,
        "confidence": confidence,
        "bullish": bullish_signals,
        "bearish": bearish_signals,
        "insider_count": len(insider_signals),
        "news_count": len(news_signals),
    }

def test_edge_cases():
    """测试边界情况：无效 ticker 和空数据"""
    print("\n" + "="*80)
    print("测试边界情况：无效 ticker")
    print("="*80)
    result = test_sentiment_for_ticker("INVALID_TICKER_XYZ", "2026-07-24")
    assert result["signal"] == "neutral" and result["confidence"] == 0.0, "无效 ticker 应返回 neutral 且置信度为 0"
    print("✅ 无效 ticker 测试通过")

def main():
    print("="*80)
    print("测试 sentiment_analyst_agent 的数据和信号合成")
    print("="*80)
    print(f"USE_EDGAR = {os.environ.get('USE_EDGAR', '未设置')}")
    print(f"USE_YFINANCE = {os.environ.get('USE_YFINANCE', '未设置')}")
    
    end_date = "2026-07-24"
    tickers = ["AAPL", "MSFT", "GOOGL"]
    results = {}
    for ticker in tickers:
        results[ticker] = test_sentiment_for_ticker(ticker, end_date)
    
    # 汇总
    print("\n" + "="*80)
    print("测试汇总")
    print("="*80)
    for ticker, res in results.items():
        print(f"{ticker}: 信号={res['signal']}, 置信度={res['confidence']:.1f}%, 内幕={res['insider_count']}, 新闻={res['news_count']}")
    
    # 边界测试
    test_edge_cases()
    
    print("\n所有测试完成。")

if __name__ == "__main__":
    main()
