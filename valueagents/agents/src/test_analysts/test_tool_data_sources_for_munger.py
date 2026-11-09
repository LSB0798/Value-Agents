#!/usr/bin/env python
"""
测试 Finnhub 和 Alpha Vantage 两个数据源
为 Charlie Munger Agent 筛选内幕交易和公司新闻数据
直接调用 API，不依赖已有工具函数
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

# ==================== 配置 ====================
TICKER = "AAPL"
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "d8tr0gpr01qhcnk5oj3gd8tr0gpr01qhcnk5oj40")
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "LEPNUFM9ZGGRXWDR")

# 时间范围：过去 30 天新闻，内幕交易从年初至今
END_DATE = datetime.now().strftime("%Y-%m-%d")
NEWS_START = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
INSIDER_START = "2026-01-01"  # 从今年初开始

# ==================== Finnhub 数据获取 ====================
def fetch_finnhub_insider(ticker):
    """获取 Finnhub 内幕交易数据"""
    url = f"https://finnhub.io/api/v1/stock/insider-transactions"
    params = {
        "symbol": ticker,
        "from": INSIDER_START,
        "token": FINNHUB_API_KEY
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', [])
    except Exception as e:
        print(f"❌ Finnhub 内幕交易请求失败: {e}")
        return []

def fetch_finnhub_news(ticker):
    """获取 Finnhub 公司新闻"""
    url = f"https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": ticker,
        "from": NEWS_START,
        "to": END_DATE,
        "token": FINNHUB_API_KEY
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Finnhub 新闻请求失败: {e}")
        return []

# ==================== Alpha Vantage 数据获取 ====================
def fetch_alpha_vantage_news(ticker):
    """获取 Alpha Vantage 新闻数据"""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "limit": 10,  # 免费版最多 10 条
        "apikey": ALPHA_VANTAGE_API_KEY,
        "sort": "LATEST"
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "Error Message" in data:
            print(f"⚠️ Alpha Vantage 错误: {data['Error Message']}")
            return []
        return data.get('feed', [])
    except Exception as e:
        print(f"❌ Alpha Vantage 新闻请求失败: {e}")
        return []

# ==================== 数据统计与分析 ====================
def analyze_insider_data(records, source_name):
    """统计内幕交易数据"""
    print(f"\n📊 {source_name} - 内幕交易统计")
    print("-" * 50)
    if not records:
        print("  ⚠️ 无数据")
        return
    total = len(records)
    buys = sum(1 for r in records if r.get('change', 0) > 0)
    sells = sum(1 for r in records if r.get('change', 0) < 0)
    gifts = sum(1 for r in records if r.get('transactionCode') == 'G')
    print(f"  总记录数: {total}")
    print(f"  买入: {buys}, 卖出: {sells}, 赠与: {gifts}")
    # 展示前 5 条关键字段
    # print("\n  样本记录 (最多 5 条):")
    for i, r in enumerate(records): # [:5]
        name = r.get('name', 'Unknown')
        change = r.get('change', 0)
        price = r.get('transactionPrice', 'N/A')
        date = r.get('transactionDate', 'N/A')
        code = r.get('transactionCode', 'N/A')
        print(f"    {i+1}. {name} | {code} | 变动: {change} | 价格: {price} | 日期: {date}")

def analyze_news_data(records, source_name):
    """统计新闻数据"""
    print(f"\n📊 {source_name} - 公司新闻统计")
    print("-" * 50)
    if not records:
        print("  ⚠️ 无数据")
        return
    total = len(records)
    print(f"  总新闻数: {total}")
    # 检查时间范围
    timestamps = [r.get('datetime') for r in records if 'datetime' in r]
    if timestamps:
        # Finnhub 返回时间戳，Alpha Vantage 返回字符串
        if isinstance(timestamps[0], int):
            dates = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps if ts]
        else:
            dates = [ts[:10] for ts in timestamps if ts]  # 字符串取前10字符
        unique_dates = sorted(set(dates))
        print(f"  日期范围: {unique_dates[0] if unique_dates else 'N/A'} 至 {unique_dates[-1] if unique_dates else 'N/A'}")
    # 展示前 5 条
    # print("\n  样本记录 (最多 5 条):")
    for i, r in enumerate(records): # [:5]
        # Finnhub 字段
        headline = r.get('headline') or r.get('title', '')
        source = r.get('source') or r.get('source', 'Unknown')
        dt = r.get('datetime')
        if dt and isinstance(dt, int):
            dt_str = datetime.fromtimestamp(dt).strftime('%Y-%m-%d %H:%M')
        else:
            dt_str = r.get('time_published', '')[:16] if 'time_published' in r else 'N/A'
        summary = r.get('summary') or r.get('summary', '')
        print(f"    {i+1}. [{dt_str}] {headline[:60]}... (来源: {source})")

# ==================== 主程序 ====================
def main():
    print(f"🔍 测试数据源: Finnhub + Alpha Vantage")
    print(f"股票: {TICKER}")
    print(f"新闻时间范围: {NEWS_START} 至 {END_DATE}")
    print(f"内幕交易起始: {INSIDER_START}")
    print("=" * 70)

    # 1. Finnhub 内幕交易
    print("\n⏳ 获取 Finnhub 内幕交易...")
    fin_insider = fetch_finnhub_insider(TICKER)
    analyze_insider_data(fin_insider, "Finnhub")

    # 2. Finnhub 新闻
    print("\n⏳ 获取 Finnhub 新闻...")
    fin_news = fetch_finnhub_news(TICKER)
    analyze_news_data(fin_news, "Finnhub")

    # 3. Alpha Vantage 新闻
    print("\n⏳ 获取 Alpha Vantage 新闻...")
    av_news = fetch_alpha_vantage_news(TICKER)
    analyze_news_data(av_news, "Alpha Vantage")

    # 综合对比
    print("\n" + "=" * 70)
    print("📈 综合对比")
    print("-" * 70)
    print(f"Finnhub 内幕交易: {len(fin_insider)} 条")
    print(f"Finnhub 新闻: {len(fin_news)} 条")
    print(f"Alpha Vantage 新闻: {len(av_news)} 条")
    if len(fin_news) > 0 and len(av_news) > 0:
        print("建议: 优先使用 Finnhub 作为主要数据源，Alpha Vantage 可作为备选。")
    elif len(fin_news) > 0:
        print("建议: 仅使用 Finnhub 即可满足需求。")
    else:
        print("⚠️ 两个数据源均无数据，请检查 API Key 或网络。")

    print("\n✅ 测试完成。")

if __name__ == "__main__":
    main()
