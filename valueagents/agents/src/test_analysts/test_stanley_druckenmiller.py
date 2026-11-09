# test_stanley_druckenmiller.py
import os
import sys
sys.path.insert(0, '/data/lishuaibing/valueagents/ValueAgents')

os.environ["USE_YFINANCE"] = "true"
os.environ["USE_EDGAR"] = "true"

from valueagents.agents.src.graph.state import AgentState
from valueagents.agents.src.analysts.stanley_druckenmiller import stanley_druckenmiller_agent

print("=== 测试 Stanley Druckenmiller Agent ===\n")

# 构建 state，注意不设置 start_date
state = AgentState(
    data={
        "tickers": ["MSFT"],
        "end_date": "2026-07-09",
        # start_date 故意不设置，让代码自动回退
        "analyst_signals": {}
    },
    metadata={"show_reasoning": False}
)

# 运行 agent
result = stanley_druckenmiller_agent(state, agent_id="stanley_druckenmiller_agent")

print("\n=== 最终信号 ===")
print(state["data"]["analyst_signals"])
