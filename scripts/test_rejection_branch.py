# scripts/test_rejection_branch.py
"""强制触发 orchestrator 的 rejection 分支（绕过 prompt 约束）。"""
import os
os.environ.setdefault("OPENAI_API_KEY", "dummy")

from langchain_core.messages import AIMessage
from valueagents.orchestrators.conversational import ConversationalOrchestrator
from valueagents.orchestrators.artifact_store import ArtifactStore
from valueagents.orchestrators.skill_catalog import SkillCatalog


def test_rejection():
    store = ArtifactStore("GOOGL", "2026-06-20")
    
    # 直接测 SkillCatalog 的 requires 校验（不经过 LLM）
    ok, missing = SkillCatalog.check_requires("portfolio_manager", store)
    print(f"portfolio_manager requires OK? {ok}")
    print(f"missing: {missing}")
    
    assert not ok, "Should not be OK with empty artifacts"
    assert "market_report" in missing
    assert "investment_plan" in missing
    assert "risk_debate_state" in missing
    print("✅ SkillCatalog.check_requires correctly rejects")
    
    # 测 render_rejection_message 输出格式
    from valueagents.orchestrators.prompts import render_rejection_message
    msg = render_rejection_message("portfolio_manager", missing, store.summary())
    print(f"\nrejection message:\n{msg}")
    assert "missing required artifacts" in msg
    assert "market_report" in msg
    print("✅ render_rejection_message correct")


if __name__ == "__main__":
    test_rejection()
    print("\n🎉 Rejection branch verified (via unit test)")
