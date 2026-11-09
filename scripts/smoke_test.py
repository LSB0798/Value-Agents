# scripts/smoke_test.py
"""
Graph 编译冒烟测试（阶段 3 适配版）。

验证：
  1. graph 能编译
  2. 节点结构符合阶段 3：
     - 有 Research Team（替代 Bull Researcher / Bear Researcher / Research Manager）
     - 无 tools_xxx（阶段 1 已删）
     - 无 Aggressive/Neutral/Conservative Analyst（阶段 2 已删）
     - 无 Bull Researcher / Bear Researcher / Research Manager（阶段 3 已删）
  3. master mode 被拒绝
  4. 单 analyst 不崩

用法：python scripts/smoke_test.py
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "dummy")

from valueagents.graph.setup import GraphSetup
from valueagents.graph.conditional_logic import ConditionalLogic
from valueagents.agents.utils.memory import FinancialSituationMemory
from valueagents.llm_clients import create_llm_client
from valueagents.default_config import DEFAULT_CONFIG


# ============================================================
# 阶段 3 期望节点（4 analyst 场景，共 14 个）
# ============================================================
EXPECTED_NODES_FULL = {
    "__start__", "__end__",
    "Market Analyst", "Msg Clear Market",
    "Social Analyst", "Msg Clear Social",
    "News Analyst", "Msg Clear News",
    "Fundamentals Analyst", "Msg Clear Fundamentals",
    "Research Team",              # 阶段 3
    "Trader",
    "Risk Team",                  # 阶段 2
    "Portfolio Manager",
}

# 明确禁止的节点（历史阶段删除的）
FORBIDDEN_NODES = {
    # 阶段 1 删除
    "tools_market", "tools_social", "tools_news", "tools_fundamentals",
    # 阶段 2 删除
    "Aggressive Analyst", "Neutral Analyst", "Conservative Analyst",
    # 阶段 3 删除（被 Research Team 替代）
    "Bull Researcher", "Bear Researcher", "Research Manager",
}


def build_graph_setup() -> GraphSetup:
    cfg = DEFAULT_CONFIG.copy()
    client = create_llm_client(
        provider=cfg["llm_provider"],
        model=cfg["quick_think_llm"],
        base_url=cfg.get("backend_url"),
    )
    llm = client.get_llm()

    return GraphSetup(
        quick_thinking_llm=llm,
        deep_thinking_llm=llm,
        tool_nodes={},
        bull_memory=FinancialSituationMemory("bull_memory", cfg),
        bear_memory=FinancialSituationMemory("bear_memory", cfg),
        trader_memory=FinancialSituationMemory("trader_memory", cfg),
        invest_judge_memory=FinancialSituationMemory("invest_judge_memory", cfg),
        portfolio_manager_memory=FinancialSituationMemory("portfolio_manager_memory", cfg),
        conditional_logic=ConditionalLogic(
            min_debate_rounds=1, max_debate_rounds=2, max_risk_discuss_rounds=1,
        ),
        min_debate_rounds=1,
        max_debate_rounds=2,
    )


def test_normal_mode():
    print("=" * 60)
    print("Test 1: normal mode (4 analysts)")
    print("=" * 60)

    gs = build_graph_setup()
    g = gs.setup_graph(
        ["market", "social", "news", "fundamentals"],
        use_master_analysts=False,
    )
    nodes = set(g.get_graph().nodes.keys())
    print(f"  Node count: {len(nodes)}")
    print(f"  Nodes: {sorted(nodes)}")

    # 断言 1：必需节点都在
    missing = EXPECTED_NODES_FULL - nodes
    assert not missing, f"❌ missing nodes: {missing}"

    # 断言 2：禁止节点都不在
    forbidden_present = FORBIDDEN_NODES & nodes
    assert not forbidden_present, f"❌ forbidden nodes present: {forbidden_present}"

    # 断言 3：节点数在合理范围（不硬编码，防未来加节点误报）
    assert 12 <= len(nodes) <= 16, f"❌ node count {len(nodes)} out of range [12, 16]"

    print("  ✅ Test 1 PASSED")


def test_master_mode_rejected():
    print()
    print("=" * 60)
    print("Test 2: master mode should raise NotImplementedError")
    print("=" * 60)

    gs = build_graph_setup()
    try:
        gs.setup_graph(["market"], use_master_analysts=True)
    except NotImplementedError as e:
        print(f"  ✅ Correctly raised: {e}")
        return
    raise AssertionError("❌ master mode did NOT raise NotImplementedError")


def test_single_analyst():
    print()
    print("=" * 60)
    print("Test 3: single analyst (only market)")
    print("=" * 60)

    gs = build_graph_setup()
    g = gs.setup_graph(["market"], use_master_analysts=False)
    nodes = set(g.get_graph().nodes.keys())
    print(f"  Node count: {len(nodes)}")

    expected_single = {
        "__start__", "__end__",
        "Market Analyst", "Msg Clear Market",
        "Research Team",
        "Trader", "Risk Team", "Portfolio Manager",
    }
    missing = expected_single - nodes
    assert not missing, f"❌ missing nodes in single-analyst mode: {missing}"

    forbidden_present = FORBIDDEN_NODES & nodes
    assert not forbidden_present, f"❌ forbidden nodes present: {forbidden_present}"

    print("  ✅ Test 3 PASSED")


if __name__ == "__main__":
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 14 + "Graph Smoke Test (Phase 3)" + " " * 17 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    test_normal_mode()
    test_master_mode_rejected()
    test_single_analyst()

    print()
    print("=" * 60)
    print("🎉 ALL SMOKE TESTS PASSED")
    print("=" * 60)