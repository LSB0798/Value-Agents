#!/usr/bin/env python
"""
测试 api.py 中 get_financial_metrics 的 TTM 功能
验证从 ROIC 获取季度数据并合成 TTM 后，各字段是否被正确填充。
"""

import sys
import os
from pprint import pprint

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import get_financial_metrics

def print_metrics(metrics):
    if not metrics:
        print("❌ 未获取到任何数据")
        return

    print(f"\n✅ 获取到 {len(metrics)} 个 TTM 数据点 (按报告期降序，最新在前)\n")
    for idx, m in enumerate(metrics, 1):
        print(f"--- 数据点 {idx} ---")
        print(f"报告期          : {m.report_period}")
        print(f"营收 (TTM)      : {m.revenue:,.0f}" if m.revenue else "营收 (TTM)      : None")
        print(f"净利润 (TTM)    : {m.net_income:,.0f}" if m.net_income else "净利润 (TTM)    : None")
        print(f"EBIT (TTM)      : {m.ebit:,.0f}" if m.ebit else "EBIT (TTM)      : None")
        print(f"EBITDA (TTM)    : {m.ebitda:,.0f}" if m.ebitda else "EBITDA (TTM)    : None")
        print(f"自由现金流 (TTM): {m.free_cash_flow:,.0f}" if m.free_cash_flow else "自由现金流 (TTM): None")
        print(f"总债务          : {m.total_debt:,.0f}" if m.total_debt else "总债务          : None")
        print(f"股东权益        : {m.shareholders_equity:,.0f}" if m.shareholders_equity else "股东权益        : None")
        print(f"现金及等价物    : {m.cash:,.0f}" if hasattr(m, 'cash') and m.cash else "现金及等价物    : None")  # 注意 models.py 中可能没有 cash 字段，但我们可以从 total_debt/equity 推算，这里假设 FinancialMetrics 没有 cash，我们不会打印，如果要有，需要 models.py 增加字段，但我们可以忽略
        print(f"市值 (历史)     : {m.market_cap:,.0f}" if m.market_cap else "市值 (历史)     : None")
        print(f"企业价值 (EV)   : {m.enterprise_value:,.0f}" if m.enterprise_value else "企业价值 (EV)   : None")
        print(f"ROE (TTM)       : {m.return_on_equity:.2%}" if m.return_on_equity else "ROE (TTM)       : None")
        print(f"ROIC (TTM)      : {m.return_on_invested_capital:.2%}" if m.return_on_invested_capital else "ROIC (TTM)      : None")
        print(f"毛利率 (TTM)    : {m.gross_margin:.2%}" if m.gross_margin else "毛利率 (TTM)    : None")
        print(f"净利率 (TTM)    : {m.net_margin:.2%}" if m.net_margin else "净利率 (TTM)    : None")
        print(f"营业利润率 (TTM): {m.operating_margin:.2%}" if m.operating_margin else "营业利润率 (TTM): None")
        print(f"市销率 (P/S)    : {m.price_to_sales_ratio:.2f}" if m.price_to_sales_ratio else "市销率 (P/S)    : None")
        print(f"市净率 (P/B)    : {m.price_to_book_ratio:.2f}" if m.price_to_book_ratio else "市净率 (P/B)    : None")
        print(f"市盈率 (P/E)    : {m.price_to_earnings_ratio:.2f}" if m.price_to_earnings_ratio else "市盈率 (P/E)    : None")
        print(f"FCF 收益率     : {m.free_cash_flow_yield:.2%}" if m.free_cash_flow_yield else "FCF 收益率     : None")
        print(f"EPS (TTM)       : {m.earnings_per_share:.2f}" if m.earnings_per_share else "EPS (TTM)       : None")
        print(f"FCF per share   : {m.free_cash_flow_per_share:.2f}" if m.free_cash_flow_per_share else "FCF per share   : None")
        print(f"BVPS            : {m.book_value_per_share:.2f}" if m.book_value_per_share else "BVPS            : None")
        print(f"Beta            : {m.beta:.2f}" if m.beta else "Beta            : None")
        print(f"营收增长率 (YoY): {m.revenue_growth:.2%}" if m.revenue_growth else "营收增长率 (YoY): None")
        print(f"净利润增长率    : {m.earnings_growth:.2%}" if m.earnings_growth else "净利润增长率    : None")
        print(f"FCF 增长率      : {m.free_cash_flow_growth:.2%}" if m.free_cash_flow_growth else "FCF 增长率      : None")
        print(f"EPS 增长率      : {m.earnings_per_share_growth:.2%}" if m.earnings_per_share_growth else "EPS 增长率      : None")
        print(f"BVPS 增长率     : {m.book_value_growth:.2%}" if m.book_value_growth else "BVPS 增长率     : None")
        print(f"PEG 比率        : {m.peg_ratio:.2f}" if m.peg_ratio else "PEG 比率        : None")
        print()

def main():
    ticker = "AAPL"
    end_date = "2026-07-23"  # 当前日期，可改为任意
    limit = 3

    print(f"🔍 测试 get_financial_metrics(period='ttm')")
    print(f"股票: {ticker}, 结束日期: {end_date}, 限制数量: {limit}\n")

    try:
        metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=limit)
        print_metrics(metrics)
    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
