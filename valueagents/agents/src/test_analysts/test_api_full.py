#!/usr/bin/env python
"""
全面测试 api.py 的所有关键函数
"""

import os
import sys
import time
from datetime import datetime, timedelta

# 确保项目路径正确
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import (
    get_prices,
    get_financial_metrics,
    search_line_items,
    get_market_cap,
    get_insider_trades,
    get_company_news,
)

def print_section(title):
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def test_get_prices():
    print_section("测试 get_prices (yfinance)")
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"参数: ticker={ticker}, start={start_date}, end={end_date}")
    prices = get_prices(ticker, start_date, end_date)
    if prices:
        print(f"✅ 返回 {len(prices)} 条记录")
        print(f"最新一条: {prices[-1].model_dump()}")
    else:
        print("❌ 返回空列表")

def test_get_financial_metrics():
    print_section("测试 get_financial_metrics")
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    for period in ["ttm", "annual", "quarterly"]:
        print(f"\n--- period={period} ---")
        metrics = get_financial_metrics(ticker, end_date, period=period, limit=3)
        if metrics:
            print(f"✅ 返回 {len(metrics)} 条记录")
            for i, m in enumerate(metrics):
                print(f"  记录 {i+1}: report_period={m.report_period}")
                print(f"    revenue={m.revenue}, net_income={m.net_income}, ebit={m.ebit}")
                print(f"    fcf={m.free_cash_flow}, eps={m.earnings_per_share}, bvps={m.book_value_per_share}")
                print(f"    roe={m.return_on_equity}, roic={m.return_on_invested_capital}")
                print(f"    ps={m.price_to_sales_ratio}, pb={m.price_to_book_ratio}, fcf_yield={m.free_cash_flow_yield}")
                print(f"    revenue_growth={m.revenue_growth}, earnings_growth={m.earnings_growth}")
        else:
            print("❌ 返回空列表")
        time.sleep(2)  # 避免速率限制

def test_search_line_items():
    print_section("测试 search_line_items")
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    fields = ["revenue", "net_income", "free_cash_flow", "total_debt", "cash_and_equivalents"]
    for period in ["ttm", "annual"]:
        print(f"\n--- period={period} ---")
        items = search_line_items(ticker, fields, end_date, period=period, limit=2)
        if items:
            print(f"✅ 返回 {len(items)} 条记录")
            for i, item in enumerate(items):
                print(f"  记录 {i+1}: date={item.report_period}")
                for f in fields:
                    print(f"    {f}: {getattr(item, f, None)}")
        else:
            print("❌ 返回空列表")
        time.sleep(2)

def test_get_market_cap():
    print_section("测试 get_market_cap")
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    cap = get_market_cap(ticker, end_date)
    if cap:
        print(f"✅ 市值: {cap:,.0f}")
    else:
        print("❌ 返回 None")

def test_get_insider_trades():
    print_section("测试 get_insider_trades")
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    trades = get_insider_trades(ticker, end_date, limit=5)
    if trades:
        print(f"✅ 返回 {len(trades)} 条记录")
        for t in trades[:3]:
            print(f"  {t.name} | {t.transaction_code} | shares={t.transaction_shares} | price={t.transaction_price}")
    else:
        print("❌ 返回空列表")

def test_get_company_news():
    print_section("测试 get_company_news")
    ticker = "AAPL"
    end_date = datetime.now().strftime("%Y-%m-%d")
    news = get_company_news(ticker, end_date, limit=5)
    if news:
        print(f"✅ 返回 {len(news)} 条记录")
        for n in news[:3]:
            print(f"  {n.date} | {n.title[:60]}... | sentiment={n.sentiment}")
    else:
        print("❌ 返回空列表")

if __name__ == "__main__":
    # 设置环境变量，以便使用免费数据源
    # 默认 USE_EDGAR 可能为 false，但我们直接测试所有函数
    print("开始测试 api.py 所有功能...")

    test_get_prices()
    time.sleep(2)

    test_get_financial_metrics()
    time.sleep(2)

    test_search_line_items()
    time.sleep(2)

    test_get_market_cap()
    time.sleep(2)

    test_get_insider_trades()
    time.sleep(2)

    test_get_company_news()

    print("\n✅ 所有测试完成")
