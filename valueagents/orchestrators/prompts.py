# valueagents/orchestrators/prompts.py
"""
Prompts — ConversationalOrchestrator 的 system prompt 模板。

职责：
  - 把 SkillCatalog.all_skills() 渲染为 LLM 可读的 skill 列表（含 requires/produces）
  - 把 ArtifactStore.summary() 嵌入 prompt，让 LLM 知道"当前有什么"
  - 强制 JSON 输出格式（{"action": "call"...} / {"action": "done"...}）
  - 通过 few-shot 示例引导 LLM 遵守 requires 前置校验

设计原则：
  - prompt 每轮重新渲染（artifacts 会变）
  - 静态部分（规则 + 示例）+ 动态部分（skills / artifacts / ticker）
  - 占位符用 __XXX__，避免与 JSON 的 {} 冲突
"""

from __future__ import annotations

from typing import Any


# ============================================================
# 静态模板
# ============================================================
_SYSTEM_TEMPLATE = """You are a financial analysis orchestrator. Your job is to fulfill the user's request by calling skills in the correct order, respecting each skill's preconditions.

## Context
- Ticker: __TICKER__
- Analysis Date: __END_DATE__

**Note**: The ticker is fixed for this session. If the user wants to switch ticker, tell them to type `:new` in the REPL (not a skill call).

## How Skills Work
Each skill has:
- `requires`: list of artifact keys that MUST already exist before you call it
- `produces`: list of artifact keys that will exist after the call
- Master analyst skills (kind=master) have empty requires/produces — they return a signal only and do not write to artifacts

## Full Analysis Pipeline
When the user asks for a "full analysis", "完整分析", "全面分析", "complete analysis", "run everything", or similar, the canonical pipeline is:

1. market_analyst → market_report
2. social_analyst → sentiment_report
3. news_analyst → news_report
4. fundamentals_analyst → fundamentals_report
5. **master_team** → master_analyst_signals, master_summary
6. research_team → investment_debate_state, investment_plan
7. trader → trader_investment_plan
8. risk_team → risk_debate_state
9. portfolio_manager → final_trade_decision

Rules:
- If `master_team` is listed in "Available Skills", you MUST include it at step 5. It runs the master analysts (Buffett, Munger, etc.) that the user selected during setup. DO NOT skip it for a "full analysis" request.
- If `master_team` is NOT listed in "Available Skills" (user configured zero masters), skip step 5 and proceed from step 4 to step 6.
- Do NOT skip any other step when the user asks for a full analysis.
- If the user asks for a specific subset (e.g. "just Buffett" or "只有 research 和 trader"), do NOT run the full pipeline — call only the skills they asked for. You may skip steps the user did not request.

## Available Skills
__SKILLS__

## Current Artifacts
__ARTIFACTS__

## Precondition Check (MANDATORY)
Before calling ANY skill, you MUST verify that ALL items in its `requires` list already exist in "Current Artifacts".
If any required artifact is missing, DO NOT call that skill. Instead:
- Call the skill that produces the missing artifact first, OR
- Respond with `{{"action": "done", "answer": "..."}}` explaining what's missing

## Output Format (STRICT)
You MUST reply with valid JSON, exactly one of:
1. Call a skill:
   {{"action": "call", "skill": "<skill_name>", "args": {{}}}}

2. Finish:
   {{"action": "done", "answer": "<final response to the user>"}}

Rules:
- Output ONLY the JSON object, no markdown, no code fences, no explanations.
- One action per turn. Do not batch multiple skill calls.
- If you are unsure, prefer `done` with an explanation over guessing.

## Examples

### Example 1: Single master skill
User: "Just run Buffett on this ticker"
Assistant:
{{"action": "call", "skill": "warren_buffett_analyst", "args": {{}}}}

### Example 2: Full pipeline (start)
User: "Run the full analysis"
Assistant:
{{"action": "call", "skill": "market_analyst", "args": {{}}}}

### Example 3: Missing preconditions
User: "Give me the research decision"
(Current artifacts: empty)
Assistant:
{{"action": "done", "answer": "research_team requires market_report, sentiment_report, news_report, fundamentals_report — none are present yet. Please run the 4 analyst skills first, or ask me to run the full analysis."}}
"""


# ============================================================
# Skills 渲染
# ============================================================
_SKILL_GROUPS = [
    # (显示名, 过滤条件)
    ("Analyst Skills (leaf, no dependencies)", "analyst"),
    ("Trader & Manager Skills (leaf, with dependencies)", "manager"),
    ("Meta Skills (internal composition)", "meta"),
    ("Master Analyst Skills (19, independent signals)", "master"),
]


def _skill_group_key(skill: dict[str, Any]) -> str:
    """把 skill 分到 4 个展示组。"""
    name = skill["name"]
    kind = skill["kind"]

    if kind == "master":
        return "master"
    if kind == "meta":
        return "meta"
    # leaf
    if name.endswith("_analyst"):
        return "analyst"
    return "manager"


def _render_skills(skills: list[dict[str, Any]]) -> str:
    """把 SkillCatalog.all_skills() 渲染为 LLM 可读的 4 段文本。"""
    buckets: dict[str, list[dict[str, Any]]] = {k: [] for _, k in _SKILL_GROUPS}
    for s in skills:
        buckets[_skill_group_key(s)].append(s)

    sections: list[str] = []
    for display_name, key in _SKILL_GROUPS:
        items = buckets[key]
        if not items:
            continue

        lines = [f"### {display_name}"]
        for s in items:
            desc = s.get("description", "") or ""
            desc = desc[:120] + ("..." if len(desc) > 120 else "")
            lines.append(f"- **{s['name']}**: {desc}")
            if s["requires"]:
                lines.append(f"  requires: {s['requires']}")
            if s["produces"]:
                lines.append(f"  produces: {s['produces']}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections) if sections else "(no skills available)"


# ============================================================
# 对外接口
# ============================================================
def render_system_prompt(
    skills: list[dict[str, Any]],
    artifacts_summary: str,
    ticker: str,
    end_date: str,
) -> str:
    """渲染完整的 system prompt。

    Args:
        skills: SkillCatalog.all_skills(...) 的输出
        artifacts_summary: ArtifactStore.summary() 的输出
        ticker: 股票代码
        end_date: 分析日期

    Returns:
        完整的 system prompt 字符串（约 3000-5000 字符，取决于 skills 数量）
    """
    skills_str = _render_skills(skills)
    return (
        _SYSTEM_TEMPLATE
        .replace("__TICKER__", ticker or "N/A")
        .replace("__END_DATE__", end_date or "N/A")
        .replace("__SKILLS__", skills_str)
        .replace("__ARTIFACTS__", artifacts_summary or "(empty)")
    )


def render_feedback_message(
    skill_name: str,
    produced_keys: list[str],
    artifacts_summary: str,
) -> str:
    """skill 调用成功后的反馈消息（追加到 messages，作为 HumanMessage）。

    这个消息告诉 LLM"刚才的 skill 产出了什么"、"现在 artifacts 有什么"，
    引导 LLM 决定下一步。
    """
    keys_str = ", ".join(produced_keys) if produced_keys else "(no new artifacts)"
    return (
        f"Skill `{skill_name}` completed successfully.\n"
        f"Produced: {keys_str}\n\n"
        f"Current artifacts:\n{artifacts_summary}"
    )


def render_rejection_message(
    skill_name: str,
    missing_keys: list[str],
    artifacts_summary: str,
) -> str:
    """skill 因缺前置条件被拒绝时的反馈消息。

    LLM 收到这个后，应主动去补缺失的 artifact，或转 done 说明原因。
    """
    missing_str = ", ".join(missing_keys)
    return (
        f"Cannot call `{skill_name}`: missing required artifacts: {missing_str}.\n"
        f"Please call the skill that produces these first, or respond with "
        f'{{"action": "done", "answer": "..."}} explaining the limitation.\n\n'
        f"Current artifacts:\n{artifacts_summary}"
    )


def render_error_message(
    skill_name: str,
    error: str,
) -> str:
    """skill 执行异常时的反馈消息。"""
    return (
        f"Skill `{skill_name}` failed with an error: {error}\n"
        f"You can retry, try a different skill, or respond with "
        f'{{"action": "done", "answer": "..."}} to summarize what you have so far.'
    )


# ============================================================
# 诊断
# ============================================================
def estimate_prompt_size(
    skills: list[dict[str, Any]],
    artifacts_summary: str,
) -> dict[str, int]:
    """估算 prompt 各部分的字符数，便于监控 prompt 膨胀。"""
    skills_str = _render_skills(skills)
    return {
        "skills_section": len(skills_str),
        "artifacts_section": len(artifacts_summary or ""),
        "template_overhead": len(_SYSTEM_TEMPLATE) - len("__SKILLS__") - len("__ARTIFACTS__"),
        "estimated_total": len(_SYSTEM_TEMPLATE) + len(skills_str) + len(artifacts_summary or ""),
    }
