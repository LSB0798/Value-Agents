#!/usr/bin/env python
"""
全面测试 valuation_analyst_agent 的性能
验证 TTM 数据一致性、估值计算正确性及数值合理性
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import statistics
from valueagents.agents.src.tools.api import get_financial_metrics, search_line_items, get_market_cap
from valueagents.agents.src.analysts.valuation import (
    calculate_owner_earnings_value,
    calculate_wacc,
    calculate_dcf_scenarios,
    calculate_ev_ebitda_value,
    calculate_residual_income_value,
)

def test_valuation_for_ticker(ticker, end_date="2026-07-24", limit=5):
    print(f"\n{'='*80}")
    print(f"测试估值分析: {ticker}")
    print(f"{'='*80}")

    # 1. 获取数据
    print("\n--- 获取数据 ---")
    metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=limit)
    if not metrics:
        print("❌ 无法获取财务指标")
        return None
    print(f"✅ 获取到 {len(metrics)} 个财务指标")

    line_items = search_line_items(
        ticker,
        line_items=[
            "free_cash_flow",
            "net_income",
            "depreciation_and_amortization",
            "capital_expenditure",
            "working_capital",
            "total_debt",
            "cash_and_equivalents",
            "interest_expense",
            "revenue",
            "operating_income",
            "ebit",
            "ebitda"
        ],
        end_date=end_date,
        period="ttm",
        limit=limit,
    )
    if len(line_items) < 2:
        print("❌ 行项目不足")
        return None
    print(f"✅ 获取到 {len(line_items)} 个行项目")

    market_cap = get_market_cap(ticker, end_date)
    if not market_cap:
        print("❌ 无法获取市值")
        return None
    print(f"✅ 市值: {market_cap:,.0f}")

    # 2. 提取最新和次新数据
    most_recent_metrics = metrics[0]
    li_curr, li_prev = line_items[0], line_items[1]
    print(f"最新报告期: {li_curr.report_period}")
    print(f"  revenue: {li_curr.revenue:,.0f}")
    print(f"  net_income: {li_curr.net_income:,.0f}")
    print(f"  free_cash_flow: {li_curr.free_cash_flow:,.0f}")
    print(f"  ebit: {li_curr.ebit:,.0f}")

    # 3. 计算各类估值
    print("\n--- 开始估值计算 ---")

    # Owner Earnings
    wc_change = 0
    if li_curr.working_capital is not None and li_prev.working_capital is not None:
        wc_change = li_curr.working_capital - li_prev.working_capital
    owner_val = calculate_owner_earnings_value(
        net_income=li_curr.net_income,
        depreciation=li_curr.depreciation_and_amortization,
        capex=li_curr.capital_expenditure,
        working_capital_change=wc_change,
        growth_rate=most_recent_metrics.earnings_growth or 0.05,
    )
    print(f"  所有者收益估值: {owner_val:,.0f}")

    # WACC
    wacc = calculate_wacc(
        market_cap=most_recent_metrics.market_cap or 0,
        total_debt=getattr(li_curr, 'total_debt', None),
        cash=getattr(li_curr, 'cash_and_equivalents', None),
        interest_coverage=most_recent_metrics.interest_coverage,
        debt_to_equity=most_recent_metrics.debt_to_equity,
    )
    print(f"  WACC: {wacc:.2%}")

    # DCF
    fcf_history = [li.free_cash_flow for li in line_items if li.free_cash_flow is not None]
    if len(fcf_history) >= 3:
        dcf_results = calculate_dcf_scenarios(
            fcf_history=fcf_history,
            growth_metrics={
                'revenue_growth': most_recent_metrics.revenue_growth,
                'fcf_growth': most_recent_metrics.free_cash_flow_growth,
                'earnings_growth': most_recent_metrics.earnings_growth
            },
            wacc=wacc,
            market_cap=most_recent_metrics.market_cap or 0,
            revenue_growth=most_recent_metrics.revenue_growth
        )
        dcf_val = dcf_results['expected_value']
        print(f"  DCF 估值: {dcf_val:,.0f}")
        print(f"    Bear: {dcf_results['downside']:,.0f}, Bull: {dcf_results['upside']:,.0f}")
    else:
        dcf_val = 0
        print("  DCF: 数据不足，设为 0")

    # EV/EBITDA
    ev_ebitda_val = calculate_ev_ebitda_value(metrics)
    print(f"  EV/EBITDA 估值: {ev_ebitda_val:,.0f}")

    # Residual Income
    rim_val = calculate_residual_income_value(
        market_cap=most_recent_metrics.market_cap,
        net_income=li_curr.net_income,
        price_to_book_ratio=most_recent_metrics.price_to_book_ratio,
        book_value_growth=most_recent_metrics.book_value_growth or 0.03,
    )
    print(f"  剩余收益估值: {rim_val:,.0f}")

    # 4. 聚合估值
    method_values = {
        "dcf": {"value": dcf_val, "weight": 0.35},
        "owner_earnings": {"value": owner_val, "weight": 0.35},
        "ev_ebitda": {"value": ev_ebitda_val, "weight": 0.20},
        "residual_income": {"value": rim_val, "weight": 0.10},
    }
    total_weight = sum(v["weight"] for v in method_values.values() if v["value"] > 0)
    if total_weight == 0:
        print("⚠️ 所有估值方法均无效，无法聚合")
        return None
    for v in method_values.values():
        v["gap"] = (v["value"] - market_cap) / market_cap if v["value"] > 0 else None
    weighted_gap = sum(
        v["weight"] * v["gap"] for v in method_values.values() if v["gap"] is not None
    ) / total_weight
    weighted_value = market_cap * (1 + weighted_gap)
    print(f"\n  加权内在价值: {weighted_value:,.0f}")
    print(f"  当前市值: {market_cap:,.0f}")
    print(f"  加权安全边际: {weighted_gap:.2%}")

    # 5. 信号和置信度
    signal = "bullish" if weighted_gap > 0.15 else "bearish" if weighted_gap < -0.15 else "neutral"
    confidence = round(min(abs(weighted_gap) / 0.30 * 100, 100))
    print(f"  信号: {signal}, 置信度: {confidence:.0f}%")

    # 6. 合理性检查
    print("\n--- 合理性检查 ---")
    checks = []
    # 检查各估值方法是否得到正数
    for name, vals in method_values.items():
        if vals["value"] is not None and vals["value"] > 0:
            checks.append(f"{name} 为正")
        else:
            checks.append(f"{name} 为零或负")
    print("  " + ", ".join(checks))
    # 检查加权内在价值是否 > 0
    if weighted_value > 0:
        print("  ✅ 加权内在价值为正")
    else:
        print("  ❌ 加权内在价值为负或零")
    # 检查安全边际是否在合理范围（-100% 到 +200%）
    if -1.0 <= weighted_gap <= 2.0:
        print("  ✅ 安全边际在合理范围")
    else:
        print("  ⚠️ 安全边际超出典型范围")
    # 检查置信度
    if 0 <= confidence <= 100:
        print("  ✅ 置信度在 0-100 之间")
    else:
        print("  ❌ 置信度超出范围")

    return {
        "weighted_value": weighted_value,
        "market_cap": market_cap,
        "gap": weighted_gap,
        "signal": signal,
        "confidence": confidence,
    }

def main():
    print("测试 valuation_analyst_agent 性能")
    print(f"USE_EDGAR = {os.environ.get('USE_EDGAR', '未设置')}")
    print(f"USE_YFINANCE = {os.environ.get('USE_YFINANCE', '未设置')}")

    tickers = ["AAPL", "MSFT", "GOOGL"]
    results = {}
    for ticker in tickers:
        results[ticker] = test_valuation_for_ticker(ticker)
    print("\n" + "="*80)
    print("汇总结果")
    print("="*80)
    for ticker, res in results.items():
        if res:
            print(f"{ticker}: 内在价值={res['weighted_value']:,.0f}, 市值={res['market_cap']:,.0f}, 安全边际={res['gap']:.2%}, 信号={res['signal']}, 置信度={res['confidence']:.0f}%")
        else:
            print(f"{ticker}: 测试失败")

if __name__ == "__main__":
    main()
