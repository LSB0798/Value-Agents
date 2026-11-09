# test_damodaran_debug.py
import os
import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')  # 根据实际路径调整

from valueagents.agents.src.tools.api import get_financial_metrics, search_line_items, get_market_cap
from valueagents.agents.src.utils.api_key import get_api_key_from_state

# 设置环境变量（可选）
os.environ["USE_EDGAR"] = "false"   # 如果使用 yfinance，设为 false
os.environ["USE_YFINANCE"] = "true"
os.environ["FINANCIAL_DATASETS_API_KEY"] = "your_key"  # 如果回退付费

ticker = "AAPL"
# ticker = "MSFT"
end_date = "2026-07-09"  # 使用一个具体日期

print("=== Testing get_financial_metrics ===")
metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=5)
for m in metrics[:3]:
    print(f"  {m.report_period}: revenue={m.revenue}, fcf={m.free_cash_flow}, market_cap={m.market_cap}")

print("\n=== Testing search_line_items ===")
line_items = search_line_items(ticker, ["free_cash_flow", "ebit", "outstanding_shares", "total_debt"],
                               end_date, period="ttm", limit=5)
for item in line_items[:3]:
    print(f"  {item.report_period}: fcf={item.free_cash_flow}, shares={item.outstanding_shares}, debt={item.total_debt}")

print("\n=== Testing get_market_cap ===")
market_cap = get_market_cap(ticker, end_date)
print(f"  Market cap: {market_cap}")



# 测试 DCF 计算
from valueagents.agents.src.analysts.aswath_damodaran import calculate_intrinsic_value_dcf

# 模拟 risk_analysis（因为当前测试未提供）
risk_analysis = {"cost_of_equity": 0.075, "beta": 0.9}

print("\n=== Testing calculate_intrinsic_value_dcf ===")
dcf_result = calculate_intrinsic_value_dcf(metrics, line_items, risk_analysis)
print(f"  Intrinsic Value (total): {dcf_result.get('intrinsic_value')}")
print(f"  Intrinsic Value (per share): {dcf_result.get('intrinsic_per_share')}")
print(f"  Assumptions: {dcf_result.get('assumptions')}")
