import os
import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')

os.environ["USE_YFINANCE"] = "false"
os.environ["USE_EDGAR"] = "true"

from valueagents.agents.src.graph.state import AgentState
from valueagents.agents.src.analysts.rakesh_jhunjhunwala import rakesh_jhunjhunwala_agent

print("=== 测试 Rakesh Jhunjhunwala Agent ===\n")

state = AgentState(
    data={
        "tickers": ["MSFT"],
        "end_date": "2026-07-09",
        "analyst_signals": {}
    },
    metadata={"show_reasoning": False}
)

result = rakesh_jhunjhunwala_agent(state, agent_id="rakesh_jhunjhunwala_agent")

print("\n=== 最终信号 ===")
print(state["data"]["analyst_signals"])
