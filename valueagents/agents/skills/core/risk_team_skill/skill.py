# valueagents/agents/skills/core/risk_team_skill/skill.py
"""
Risk Team Meta Skill

替代 graph 里的 3 个 debator 节点 + 3 条 conditional_edges。
内部 while 循环 + 每轮滚动压缩 history（P0 修复）。
"""

from valueagents.agents.skills.contract import SkillContext, SkillResult
from valueagents.agents.skills.policies.debate import DebatePolicy


# ============================================================
# 压缩配置
# ============================================================
_HISTORY_THRESHOLD = 30000       # 超过这个字符数开始压缩
_KEEP_TAIL_CHARS = 15000          # 保留尾部完整内容
_SUMMARY_MAX_WORDS = 400          # 摘要目标词数（约 2500-3000 chars）


# ============================================================
# 前置校验
# ============================================================
_REQUIRED_KEYS = (
    "company_of_interest",
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "trader_investment_plan",
)


def _validate_artifacts(ctx: SkillContext) -> list[str]:
    return [k for k in _REQUIRED_KEYS if k not in ctx.artifacts]


# ============================================================
# 初始 risk_debate_state（与 propagation.py 对齐）
# ============================================================
def _initial_risk_state() -> dict:
    return {
        "history": "",
        "aggressive_history": "",
        "conservative_history": "",
        "neutral_history": "",
        "latest_speaker": "",
        "current_aggressive_response": "",
        "current_conservative_response": "",
        "current_neutral_response": "",
        "judge_decision": "",
        "count": 0,
    }


# ============================================================
# History 滚动压缩（P0 核心）
# ============================================================
def _compress_history(risk_state: dict) -> dict:
    """
    当 history 超过阈值时，保留尾部完整，前部压缩成摘要。

    策略：
      - history ≤ 30000：不压
      - history > 30000：保留最后 15000 chars 完整，前部用 compress_text 压成 400 词摘要
      - 压缩失败则 safe_truncate 兜底

    只压 history 字段；3 个 *_history 字段不压（每个 debator 自己维护）。
    """
    history = risk_state.get("history", "")
    if len(history) <= _HISTORY_THRESHOLD:
        return risk_state

    keep_tail = min(_KEEP_TAIL_CHARS, len(history) // 2)
    tail = history[-keep_tail:]
    head = history[:-keep_tail]

    compressed_head: str
    try:
        from valueagents.agents.utils.compress_utils import compress_text
        compressed_head = compress_text(
            text=head,
            max_words=_SUMMARY_MAX_WORDS,
            role="risk debate history (early rounds)",
            query_reason="compress earlier rounds to reduce prompt size while preserving key arguments",
            context=None,
        )
        print(
            f"   🗜️  [risk_team] history compressed: "
            f"{len(history)} -> {len(compressed_head) + keep_tail + 100} chars "
            f"(head {len(head)}->{len(compressed_head)}, tail {keep_tail} full)"
        )
    except Exception as e:
        from valueagents.agents.utils.compress_utils import safe_truncate
        compressed_head = safe_truncate(head, max_chars=_HISTORY_THRESHOLD // 4)
        print(f"   ⚠️  [risk_team] history compression failed ({e}); fallback to truncate")

    new_state = dict(risk_state)   # 不原地修改
    new_state["history"] = (
        f"[=== Earlier Rounds (compressed summary) ===]\n"
        f"{compressed_head}\n\n"
        f"[=== Recent Rounds (full) ===]\n"
        f"{tail}"
    )
    return new_state


# ============================================================
# 主入口
# ============================================================
def execute(ctx: SkillContext) -> SkillResult:
    missing = _validate_artifacts(ctx)
    if missing:
        return SkillResult(
            outputs={"risk_debate_state": ctx.artifacts.get("risk_debate_state") or _initial_risk_state()},
            metadata={"agent": "risk_team", "error": f"missing: {missing}"},
        )

    # 延迟 import
    from valueagents.agents.risk_mgmt.aggressive_debator import create_aggressive_debator
    from valueagents.agents.risk_mgmt.conservative_debator import create_conservative_debator
    from valueagents.agents.risk_mgmt.neutral_debator import create_neutral_debator

    aggressive_fn = create_aggressive_debator(ctx.llm)
    conservative_fn = create_conservative_debator(ctx.llm)
    neutral_fn = create_neutral_debator(ctx.llm)

    # 初始化（可从 ctx 继承，也可全新建）
    risk_state = ctx.artifacts.get("risk_debate_state") or _initial_risk_state()
    if not risk_state.get("history"):
        risk_state = _initial_risk_state()

    # 最大轮数（从 metadata._config 拿，缺失则默认 1）
    cfg = (ctx.config or {})
    max_rounds = int(cfg.get("max_risk_discuss_rounds", 1))
    max_iter = max_rounds + 1   # 安全上限

    print(f"\n   🛡️  [risk_team] starting debate: max_rounds={max_rounds}")

    for round_idx in range(max_iter):
        print(f"\n   ── Round {round_idx + 1}/{max_rounds} ──")

        # 🆕 每轮开头压一次 history（若超阈值）
        risk_state = _compress_history(risk_state)

        # 3 人依次发言
        for name, debator_fn in (
            ("Aggressive", aggressive_fn),
            ("Conservative", conservative_fn),
            ("Neutral", neutral_fn),
        ):
            state_for_debator = {**ctx.artifacts, "risk_debate_state": risk_state}
            result = debator_fn(state_for_debator)
            risk_state = result["risk_debate_state"]

        # 停止判据
        should_stop, reason = DebatePolicy.should_stop_risk(risk_state, max_rounds)
        if should_stop:
            risk_state = dict(risk_state)
            risk_state["stop_reason"] = reason
            print(f"   🛑 [risk_team] stop: {reason} (count={risk_state['count']})")
            break

    final_history_len = len(risk_state.get("history", ""))
    print(f"   🛡️  [risk_team] done: count={risk_state['count']} "
          f"rounds={risk_state['count'] // 3} history_len={final_history_len}")

    return SkillResult(
        outputs={"risk_debate_state": risk_state},
        metadata={
            "agent": "risk_team",
            "rounds": risk_state["count"] // 3,
            "stop_reason": risk_state.get("stop_reason", ""),
            "final_history_len": final_history_len,
        },
    )
