import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')

from valueagents.agents.src.tools.api import _fetch_edgar_annual_data

ticker = "AAPL"
print("第一次调用（应触发 SEC 获取并缓存）:")
data1 = _fetch_edgar_annual_data(ticker)
print(f"income shape: {data1['income'].shape}, balance: {data1['balance'].shape}, cashflow: {data1['cashflow'].shape}")

print("\n第二次调用（应从缓存读取）:")
data2 = _fetch_edgar_annual_data(ticker)
print(f"income shape: {data2['income'].shape}, balance: {data2['balance'].shape}, cashflow: {data2['cashflow'].shape}")
