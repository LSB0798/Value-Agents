# test_edgar_extraction.py
import os
import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')

# 强制启用 EDGAR
os.environ["USE_EDGAR"] = "true"
os.environ["USE_YFINANCE"] = "false"   # 确保不走 yfinance

from valueagents.agents.src.graph.state import AgentState
from valueagents.agents.src.analysts.charlie_munger import charlie_munger_agent

print("=== 测试 EDGAR 数据提取 (charlie_munger_agent) ===\n")

state = AgentState(
    data={
        "tickers": ["MSFT"],
        "end_date": "2026-07-09",
        "analyst_signals": {}
    },
    metadata={"show_reasoning": False}
)

result = charlie_munger_agent(state, agent_id="charlie_munger_agent")

print("\n=== 最终信号 ===")
print(state["data"]["analyst_signals"])
