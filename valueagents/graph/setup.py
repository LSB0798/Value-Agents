# valueagents/graph/setup.py

from typing import Any, Dict
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from valueagents.agents import *
from valueagents.agents.utils.agent_states import AgentState

from .conditional_logic import ConditionalLogic
from .adapter import skill_to_graph_node
from valueagents.agents.skills.core import load_core_skill


# ============================================================
# 核心 analyst 名称映射
# ============================================================
_CORE_ANALYST_SKILLS = {
    "market": "market_analyst_skill",
    "social": "social_analyst_skill",
    "news": "news_analyst_skill",
    "fundamentals": "fundamentals_analyst_skill",
}

_STANDARD_ANALYSTS = set(_CORE_ANALYST_SKILLS.keys())


def _node_name(analyst_type: str) -> str:
    """生成 graph 节点名。

    标准分析师：market → Market Analyst
    master 分析师：warren_buffett_analyst → Warren Buffett Analyst
    """
    if analyst_type in _STANDARD_ANALYSTS:
        return f"{analyst_type.capitalize()} Analyst"
    # master: strip _analyst suffix, snake_case → Title Case
    base = analyst_type.replace("_analyst", "")
    return f"{base.replace('_', ' ').title()} Analyst"


def signal_aggregator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """汇聚 master 分析师的信号（仅日志，不改变 state）。"""
    master_signals = state.get("master_analyst_signals", {})
    print("\n" + "=" * 60)
    print("📡 SIGNAL AGGREGATOR: Received signals from master analysts:")
    for agent, signals in master_signals.items():
        for ticker, sig in signals.items():
            print(f"   - {agent}: {ticker} -> {sig.get('signal', 'N/A')} (conf: {sig.get('confidence', 0)})")
    print("=" * 60 + "\n")
    return {}


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: Any,
        deep_thinking_llm: Any,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        portfolio_manager_memory,
        conditional_logic: ConditionalLogic,
        min_debate_rounds=1,
        max_debate_rounds=5,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm

        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.portfolio_manager_memory = portfolio_manager_memory
        self.conditional_logic = conditional_logic
        self.min_debate_rounds = min_debate_rounds
        self.max_debate_rounds = max_debate_rounds

    def setup_graph(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        use_master_analysts=False,
    ):
        print(
            f"[DEBUG] setup_graph received selected_analysts: {selected_analysts}, "
            f"use_master_analysts={use_master_analysts}"
        )

        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # ============================================================
        # 1. 创建 analyst 节点（标准 + master）
        # ============================================================
        analyst_nodes = {}
        delete_nodes = {}

        for analyst_type in selected_analysts:
            if analyst_type in _STANDARD_ANALYSTS:
                # 标准 analyst：core skill
                skill = load_core_skill(_CORE_ANALYST_SKILLS[analyst_type])
                if skill is None:
                    raise RuntimeError(
                        f"Failed to load core skill: {_CORE_ANALYST_SKILLS[analyst_type]}"
                    )
                analyst_nodes[analyst_type] = skill_to_graph_node(
                    skill, self.quick_thinking_llm
                )
                delete_nodes[analyst_type] = create_msg_delete()

            elif use_master_analysts:
                # master analyst：hf_analysts_wrapper 提供 node 函数
                from valueagents.agents.hf_analysts_wrapper import get_master_analyst_node

                print(f"   [master mode] creating node for: {analyst_type}")
                node_func = get_master_analyst_node(
                    analyst_type, self.quick_thinking_llm
                )
                analyst_nodes[analyst_type] = node_func
                delete_nodes[analyst_type] = create_msg_delete()

            else:
                raise ValueError(
                    f"Unknown analyst '{analyst_type}'. "
                    f"Supported standard analysts: {sorted(_STANDARD_ANALYSTS)}. "
                    f"For master analysts (e.g. warren_buffett_analyst), "
                    f"pass use_master_analysts=True."
                )

        # ============================================================
        # 3. 研究 / 交易 / 风险 / 组合节点
        # ============================================================
        trader_skill = load_core_skill("trader_skill")
        pm_skill = load_core_skill("portfolio_manager_skill")
        risk_team_skill = load_core_skill("risk_team_skill")
        research_team_skill = load_core_skill("research_team_skill")

        for name, skill in [
            ("trader", trader_skill),
            ("portfolio_manager", pm_skill),
            ("risk_team", risk_team_skill),
            ("research_team", research_team_skill),
        ]:
            if skill is None:
                raise RuntimeError(f"Failed to load core skill: {name}_skill")

        trader_node = skill_to_graph_node(trader_skill, self.quick_thinking_llm)
        portfolio_manager_node = skill_to_graph_node(pm_skill, self.deep_thinking_llm)
        risk_team_node = skill_to_graph_node(risk_team_skill, self.quick_thinking_llm)
        research_team_node = skill_to_graph_node(
            research_team_skill, self.quick_thinking_llm
        )

        # ============================================================
        # 4. 构建 workflow
        # ============================================================
        workflow = StateGraph(AgentState)

        # --- 4.1 analyst 节点 + clear 节点 ---
        for analyst_type, node in analyst_nodes.items():
            node_name = _node_name(analyst_type)
            clear_name = f"Msg Clear {node_name}"
            workflow.add_node(node_name, node)
            workflow.add_node(clear_name, delete_nodes[analyst_type])

        # --- 4.2 其他节点 ---
        workflow.add_node("Research Team", research_team_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risk Team", risk_team_node)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        # --- 4.2.5 master mode：加 SignalAggregator ---
        if use_master_analysts:
            workflow.add_node("SignalAggregator", signal_aggregator_node)

        # --- 4.3 analyst 串联 ---
        first_analyst_node = _node_name(selected_analysts[0])
        workflow.add_edge(START, first_analyst_node)

        for i, analyst_type in enumerate(selected_analysts):
            current_node = _node_name(analyst_type)
            current_clear = f"Msg Clear {current_node}"

            workflow.add_edge(current_node, current_clear)

            if i < len(selected_analysts) - 1:
                next_node = _node_name(selected_analysts[i + 1])
                workflow.add_edge(current_clear, next_node)
            else:
                # 最后一个 analyst 的出口
                if use_master_analysts:
                    workflow.add_edge(current_clear, "SignalAggregator")
                else:
                    workflow.add_edge(current_clear, "Research Team")

        # --- 4.4 SignalAggregator → Research Team ---
        if use_master_analysts:
            workflow.add_edge("SignalAggregator", "Research Team")

        # --- 4.5 后续链路 ---
        workflow.add_edge("Research Team", "Trader")
        workflow.add_edge("Trader", "Risk Team")
        workflow.add_edge("Risk Team", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", END)

        return workflow.compile()

    def get_round_bounds(self):
        return self.min_debate_rounds, self.max_debate_rounds