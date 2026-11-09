#!/usr/bin/env python
"""
测试 warren_buffett_agent 的数据流和分析逻辑
验证 _synthesize_ttm_line_items_from_roic 中新增字段的填充
"""

import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from valueagents.agents.src.tools.api import (
    get_financial_metrics,
    get_market_cap,
    search_line_items,
)

from valueagents.agents.src.analysts.warren_buffett import (
    analyze_fundamentals,
    analyze_consistency,
    analyze_moat,
    analyze_pricing_power,
    analyze_book_value_growth,
    analyze_management_quality,
    calculate_intrinsic_value,
)

def test_ticker(ticker, end_date):
    print(f"\n{'='*80}")
    print(f"测试 {ticker}")
    print(f"{'='*80}")

    # 1. 获取财务指标 (TTM)
    print("\n--- 1. 获取财务指标 (TTM) ---")
    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=10)
    if not metrics:
        print("❌ 未获取到财务指标")
        return
    print(f"✅ 获取到 {len(metrics)} 个 TTM 数据点")
    latest = metrics[0]
    print(f"最新报告期: {latest.report_period}")
    print(f"  ROE: {latest.return_on_equity:.2%}" if latest.return_on_equity else "  ROE: None")
    print(f"  Debt/Equity: {latest.debt_to_equity:.2f}" if latest.debt_to_equity else "  Debt/Equity: None")
    print(f"  Operating Margin: {latest.operating_margin:.2%}" if latest.operating_margin else "  Operating Margin: None")
    print(f"  Current Ratio: {latest.current_ratio:.2f}" if latest.current_ratio else "  Current Ratio: None")

    # 2. 获取行项目 (TTM)
    print("\n--- 2. 获取行项目 (TTM) ---")
    line_items = search_line_items(
        ticker,
        [
            "capital_expenditure",
            "depreciation_and_amortization",
            "net_income",
            "outstanding_shares",
            "total_assets",
            "total_liabilities",
            "shareholders_equity",
            "dividends_and_other_cash_distributions",
            "issuance_or_purchase_of_equity_shares",
            "gross_profit",
            "revenue",
            "free_cash_flow",
        ],
        end_date,
        period="ttm",
        limit=10,
    )
    if not line_items:
        print("❌ 未获取到行项目")
        return
    print(f"✅ 获取到 {len(line_items)} 条 TTM 行项目记录")
    latest_li = line_items[0]
    print(f"最新行项目报告期: {latest_li.report_period}")
    print(f"  total_assets: {latest_li.total_assets}")
    print(f"  total_liabilities: {latest_li.total_liabilities}")
    print(f"  current_assets: {latest_li.current_assets}")
    print(f"  current_liabilities: {latest_li.current_liabilities}")
    print(f"  issuance_or_purchase_of_equity_shares: {latest_li.issuance_or_purchase_of_equity_shares}")

    # 3. 运行分析函数
    print("\n--- 3. 分析函数 ---")
    # 3.1 基本面分析
    fundamental = analyze_fundamentals(metrics)
    print(f"基本面评分: {fundamental['score']}")
    print(f"细节: {fundamental['details']}")

    # 3.2 一致性分析
    consistency = analyze_consistency(line_items)
    print(f"一致性评分: {consistency['score']}")
    print(f"细节: {consistency['details']}")

    # 3.3 护城河分析
    moat = analyze_moat(metrics)
    print(f"护城河评分: {moat['score']}/{moat['max_score']}")
    print(f"细节: {moat['details']}")

    # 3.4 定价能力分析
    pricing = analyze_pricing_power(line_items, metrics)
    print(f"定价能力评分: {pricing['score']}")
    print(f"细节: {pricing['details']}")

    # 3.5 账面价值增长
    bv_growth = analyze_book_value_growth(line_items)
    print(f"账面价值增长评分: {bv_growth['score']}")
    print(f"细节: {bv_growth['details']}")

    # 3.6 管理质量
    mgmt = analyze_management_quality(line_items)
    print(f"管理质量评分: {mgmt['score']}/{mgmt['max_score']}")
    print(f"细节: {mgmt['details']}")

    # 3.7 内在价值计算
    intrinsic = calculate_intrinsic_value(line_items)
    print(f"内在价值: {intrinsic.get('intrinsic_value', 'N/A')}")
    print(f"所有者收益: {intrinsic.get('owner_earnings', 'N/A')}")
    print(f"细节: {intrinsic.get('details', 'N/A')}")

    # 4. 获取市值并计算安全边际
    market_cap = get_market_cap(ticker, end_date)
    if market_cap and intrinsic.get('intrinsic_value'):
        mos = (intrinsic['intrinsic_value'] - market_cap) / market_cap
        print(f"\n市值: {market_cap:,.0f}")
        print(f"安全边际: {mos:.2%}")
    else:
        print("\n无法计算安全边际")

    print("\n✅ 所有分析函数执行完毕，无异常。")

def main():
    print("测试 Warren Buffett Agent 数据流和分析逻辑")
    print(f"USE_EDGAR = {os.environ.get('USE_EDGAR', '未设置')}")
    print(f"USE_YFINANCE = {os.environ.get('USE_YFINANCE', '未设置')}")
    end_date = "2026-07-24"
    test_ticker("AAPL", end_date)
    test_ticker("MSFT", end_date)
    test_ticker("GOOGL", end_date)

if __name__ == "__main__":
    main()
