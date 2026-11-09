import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')
from valueagents.agents.src.tools.api import _fetch_yf_financials

ticker = "AAPL"
data1 = _fetch_yf_financials(ticker)
print(f"首次: financials={len(data1['financials'])}, balance={len(data1['balance'])}, cashflow={len(data1['cashflow'])}")

data2 = _fetch_yf_financials(ticker)
print(f"再次: financials={len(data2['financials'])}, balance={len(data2['balance'])}, cashflow={len(data2['cashflow'])}")
