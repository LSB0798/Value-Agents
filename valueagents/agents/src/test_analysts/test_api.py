#!/usr/bin/env python
"""
测试 api.py 所有函数
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta

# 添加项目根目录到 path（如果运行位置不在项目根目录）
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

def test_get_prices(ticker="AAPL"):
    print_section("测试 get_prices (yfinance)")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    print(f"参数: ticker={ticker}, start={start_date}, end={end_date}")
    try:
        prices = get_prices(ticker, start_date, end_date)
        if prices:
            print(f"✅ 获取到 {len(prices)} 条价格记录")
            print(f"最新一条: {prices[-1].model_dump()}")
        else:
            print("❌ 返回空列表")
    except Exception as e:
        print(f"❌ 异常: {e}")

def test_get_financial_metrics(ticker="AAPL"):
    print_section("测试 get_financial_metrics (ROIC)")
    end_date = datetime.now().strftime("%Y-%m-%d")
    for period in ["ttm", "annual", "quarterly"]:
        print(f"\n--- period={period} ---")
        try:
            metrics = get_financial_metrics(ticker, end_date, period=period, limit=3)
            if metrics:
                print(f"✅ 返回 {len(metrics)} 条记录")
                for i, m in enumerate(metrics):
                    print(f"  记录 {i+1}: report_period={m.report_period}")
                    print(f"    revenue={m.revenue}, net_income={m.net_income}, ebit={m.ebit}, fcf={m.free_cash_flow}")
                    print(f"    roe={m.return_on_equity}, roic={m.return_on_invested_capital}")
                    print(f"    operating_margin={m.operating_margin}, net_margin={m.net_margin}, gross_margin={m.gross_margin}")
                    print(f"    total_assets={m.total_assets}, total_liabilities={m.total_liabilities}, equity={m.shareholders_equity}")
                    print(f"    debt_to_equity={m.debt_to_equity}, current_ratio={m.current_ratio}")
            else:
                print("❌ 返回空列表")
        except Exception as e:
            print(f"❌ 异常: {e}")
        time.sleep(2)  # 避免速率限制

def test_search_line_items(ticker="AAPL"):
    print_section("测试 search_line_items (ROIC)")
    end_date = datetime.now().strftime("%Y-%m-%d")
    # 测试常用字段
    fields = [
        "revenue", "net_income", "operating_income", "free_cash_flow",
        "total_assets", "total_liabilities", "shareholders_equity",
        "cash_and_equivalents", "total_debt", "outstanding_shares",
        "earnings_per_share", "book_value_per_share",
        "current_assets", "current_liabilities", "working_capital",
        "capital_expenditure", "depreciation_and_amortization",
        "dividends_and_other_cash_distributions"
    ]
    for period in ["ttm", "annual", "quarterly"]:
        print(f"\n--- period={period} ---")
        try:
            items = search_line_items(ticker, fields, end_date, period=period, limit=2)
            if items:
                print(f"✅ 返回 {len(items)} 条记录")
                for i, item in enumerate(items):
                    print(f"  记录 {i+1}: date={item.date}, fiscal_year={item.fiscal_year}")
                    print(f"    revenue={item.revenue}, net_income={item.net_income}, operating_income={item.operating_income}")
                    print(f"    free_cash_flow={item.free_cash_flow}, capital_expenditure={item.capital_expenditure}")
                    print(f"    cash={item.cash_and_equivalents}, debt={item.total_debt}, equity={item.shareholders_equity}")
                    print(f"    shares={item.outstanding_shares}, eps={item.earnings_per_share}, bvps={item.book_value_per_share}")
                    print(f"    current_assets={item.current_assets}, current_liabilities={item.current_liabilities}")
                    print(f"    dividends={item.dividends_and_other_cash_distributions}")
            else:
                print("❌ 返回空列表")
        except Exception as e:
            print(f"❌ 异常: {e}")
        time.sleep(2)

def test_get_market_cap(ticker="AAPL"):
    print_section("测试 get_market_cap (yfinance)")
    end_date = datetime.now().strftime("%Y-%m-%d")
    try:
        cap = get_market_cap(ticker, end_date)
        if cap:
            print(f"✅ 市值: {cap:,.0f}")
        else:
            print("❌ 返回 None")
    except Exception as e:
        print(f"❌ 异常: {e}")

def test_get_insider_trades(ticker="AAPL"):
    print_section("测试 get_insider_trades (Finnhub)")
    end_date = datetime.now().strftime("%Y-%m-%d")
    try:
        trades = get_insider_trades(ticker, end_date, limit=5)
        if trades:
            print(f"✅ 获取到 {len(trades)} 条内幕交易记录")
            for t in trades[:3]:
                print(f"  {t.name} | {t.transaction_code} | shares={t.transaction_shares} | price={t.transaction_price} | date={t.transaction_date}")
        else:
            print("❌ 返回空列表")
    except Exception as e:
        print(f"❌ 异常: {e}")

def test_get_company_news(ticker="AAPL"):
    print_section("测试 get_company_news (Finnhub)")
    end_date = datetime.now().strftime("%Y-%m-%d")
    try:
        news = get_company_news(ticker, end_date, limit=5)
        if news:
            print(f"✅ 获取到 {len(news)} 条新闻")
            for n in news[:3]:
                print(f"  {n.date} | {n.title[:60]}... | sentiment={n.sentiment}")
        else:
            print("❌ 返回空列表")
    except Exception as e:
        print(f"❌ 异常: {e}")

if __name__ == "__main__":
    print("开始测试 api.py 所有功能...")
    # 清理缓存？如果需要，可删除缓存目录，但测试中我们保留缓存加速。
    # 为避免缓存影响，可先用不同 ticker 测试，但 AAPL 会命中缓存也可能没问题。
    ticker = "AAPL"
    test_get_prices(ticker)
    time.sleep(3)
    test_get_financial_metrics(ticker)
    time.sleep(3)
    test_search_line_items(ticker)
    time.sleep(3)
    test_get_market_cap(ticker)
    time.sleep(2)
    test_get_insider_trades(ticker)
    time.sleep(2)
    test_get_company_news(ticker)
    print("\n所有测试完成。")
