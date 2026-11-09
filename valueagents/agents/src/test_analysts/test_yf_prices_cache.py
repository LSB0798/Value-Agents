import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')

from valueagents.agents.src.tools.api import _fetch_yf_prices

ticker = "AAPL"
start_date = "2025-01-01"
end_date = "2025-01-31"

print("第一次调用（应下载并缓存）:")
prices1 = _fetch_yf_prices(ticker, start_date, end_date)
print(f"获取到 {len(prices1)} 条价格记录")

print("\n第二次调用（应从缓存读取）:")
prices2 = _fetch_yf_prices(ticker, start_date, end_date)
print(f"获取到 {len(prices2)} 条价格记录")
assert len(prices1) == len(prices2)
print("测试通过")
