import os
import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')  # 根据你的实际路径调整

# 强制使用 yfinance（免费数据源）
os.environ["USE_YFINANCE"] = "true"
os.environ["USE_EDGAR"] = "true"

import yfinance as yf
yf.config.network.retries = 3  # 设置重试次数，减少超时

from valueagents.agents.src.tools.api import get_financial_metrics, search_line_items, get_market_cap
from valueagents.agents.src.analysts.bill_ackman import (
    analyze_business_quality,
    analyze_financial_discipline,
    analyze_activism_potential,
    analyze_valuation,
    bill_ackman_agent
)
from valueagents.agents.src.graph.state import AgentState

# 参数设置
ticker = "AAPL"
# ticker = "MSFT"
end_date = "2026-07-09"

print("=== Testing Bill Ackman data flow ===\n")

# 1. 获取数据
print("--- Fetching financial metrics ---")
metrics = get_financial_metrics(ticker, end_date, period="annual", limit=5)
print(f"  Retrieved {len(metrics)} metrics")
for m in metrics[:2]:
    print(f"    {m.report_period}: revenue={m.revenue}, ROE={m.return_on_equity}")

print("\n--- Fetching line items ---")
line_items = search_line_items(
    ticker,
    ["revenue", "operating_margin", "debt_to_equity", "free_cash_flow",
     "total_assets", "total_liabilities", "dividends_and_other_cash_distributions",
     "outstanding_shares"],
    end_date,
    period="annual",
    limit=5
)
print(f"  Retrieved {len(line_items)} line items")
for item in line_items[:2]:
    print(f"    {item.report_period}: revenue={item.revenue}, fcf={item.free_cash_flow}, "
          f"op_margin={item.operating_margin}, shares={item.outstanding_shares}")

print("\n--- Fetching market cap ---")
market_cap = get_market_cap(ticker, end_date)
print(f"  Market cap: {market_cap}\n")

# 2. 测试各个分析函数（这些函数内部已包含调试打印）
print("=== Testing analyze_business_quality ===")
quality_result = analyze_business_quality(metrics, line_items)
print(f"  Score: {quality_result['score']}")
print(f"  Details: {quality_result['details']}\n")

print("=== Testing analyze_financial_discipline ===")
discipline_result = analyze_financial_discipline(metrics, line_items)
print(f"  Score: {discipline_result['score']}")
print(f"  Details: {discipline_result['details']}\n")

print("=== Testing analyze_activism_potential ===")
activism_result = analyze_activism_potential(line_items)
print(f"  Score: {activism_result['score']}")
print(f"  Details: {activism_result['details']}\n")

print("=== Testing analyze_valuation ===")
valuation_result = analyze_valuation(line_items, market_cap)
print(f"  Score: {valuation_result['score']}")
print(f"  Intrinsic Value: {valuation_result.get('intrinsic_value')}")
print(f"  Margin of Safety: {valuation_result.get('margin_of_safety')}")
print(f"  Details: {valuation_result['details']}\n")

# 3. 测试完整的 bill_ackman_agent（需要构造完整的 state）
print("=== Testing full bill_ackman_agent (simulated) ===")
state = AgentState(
    data={
        "tickers": [ticker],
        "end_date": end_date,
        "start_date": "2021-01-01",
        "analyst_signals": {}   # ✅ 必须包含此键，否则 agent 会 KeyError
    },
    metadata={"show_reasoning": False}
)

# 调用 agent
result = bill_ackman_agent(state, agent_id="bill_ackman_agent")
print("  Agent executed successfully.")

# 打印信号
signals = state["data"]["analyst_signals"]["bill_ackman_agent"]
print(f"  Signal for {ticker}: {signals[ticker]['signal']}, confidence: {signals[ticker]['confidence']}")
print(f"  Reasoning: {signals[ticker]['reasoning'][:300]}...")
