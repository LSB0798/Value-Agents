# valueagents/agents/skills/core/research_team_skill/skill.py
"""
Research Team Meta Skill（阶段 3）

替代 graph 里的 Bull Researcher + Bear Researcher + Research Manager 3 个节点 + 2 条 conditional_edges。

关键设计：
  1. used_skills 隔离：通过 state 传独立 dict，不改 bull/bear 源码
  2. History 滚动压缩：每轮开头压 debate_state["history"]
  3. Research Manager 在 skill 内部最后调用
"""

from valueagents.agents.skills.contract import SkillContext, SkillResult


# ============================================================
# 空 memory 兜底（与 research_manager_skill 一致）
# ============================================================
class _NullMemory:
    def get_memories(self, situation, n_matches=2):
        return []

    def add_situations(self, situations):
        pass


# ============================================================
# 压缩配置
# ============================================================
_HISTORY_THRESHOLD = 30000
_KEEP_TAIL_CHARS = 15000
_SUMMARY_MAX_WORDS = 400


# ============================================================
# 前置校验
# ============================================================
_REQUIRED_KEYS = (
    "company_of_interest",
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
)


def _validate_artifacts(ctx: SkillContext) -> list[str]:
    return [k for k in _REQUIRED_KEYS if k not in ctx.artifacts]


# ============================================================
# 初始 debate_state（与 propagation.py 对齐）
# ============================================================
def _initial_debate_state() -> dict:
    return {
        "history": "",
        "bull_history": "",
        "bear_history": "",
        "current_response": "",
        "judge_decision": "",
        "count": 0,
        "current_round": 1,
        "bull_remaining": True,
        "bear_remaining": True,
        "no_new_points_streak": 0,
        "stop_reason": "",
    }


# ============================================================
# History 滚动压缩
# ============================================================
def _compress_debate_history(debate_state: dict) -> dict:
    history = debate_state.get("history", "")
    if len(history) <= _HISTORY_THRESHOLD:
        return debate_state

    keep_tail = min(_KEEP_TAIL_CHARS, len(history) // 2)
    tail = history[-keep_tail:]
    head = history[:-keep_tail]

    try:
        from valueagents.agents.utils.compress_utils import compress_text
        compressed_head = compress_text(
            text=head,
            max_words=_SUMMARY_MAX_WORDS,
            role="research debate history (early rounds)",
            query_reason="compress earlier rounds to reduce prompt size while preserving key arguments",
            context=None,
        )
        print(f"   🗜️  [research_team] history compressed: "
              f"{len(history)} -> {len(compressed_head) + keep_tail + 100} chars "
              f"(head {len(head)}->{len(compressed_head)}, tail {keep_tail} full)")
    except Exception as e:
        from valueagents.agents.utils.compress_utils import safe_truncate
        compressed_head = safe_truncate(head, max_chars=_HISTORY_THRESHOLD // 4)
        print(f"   ⚠️  [research_team] compression failed ({e}); fallback to truncate")

    new_state = dict(debate_state)
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
            outputs={
                "investment_debate_state": ctx.artifacts.get("investment_debate_state") or _initial_debate_state(),
                "investment_plan": "",
            },
            metadata={"agent": "research_team", "error": f"missing: {missing}"},
        )

    # 🆕 Prefetch：Bull/Bear 内部会调 19 个大师 skill，也需要共享数据
    from valueagents.agents.utils.prefetch import prefetch_shared_data
    prefetch_shared_data(ctx.ticker, ctx.end_date, ctx.api_key)

    # 延迟 import
    from valueagents.agents.researchers.bull_researcher import create_bull_researcher
    from valueagents.agents.researchers.bear_researcher import create_bear_researcher
    from valueagents.agents.managers.research_manager import create_research_manager

    cfg = (ctx.config or {})
    min_rounds = int(cfg.get("min_debate_rounds", 1))
    max_rounds = int(cfg.get("max_debate_rounds", 5))

    # 初始化 debate_state（可从 state 继承）
    debate_state = ctx.artifacts.get("investment_debate_state") or _initial_debate_state()
    if not debate_state.get("current_round"):
        debate_state = _initial_debate_state()

    # Memory
    bull_memory = ctx.artifacts.get("_bull_memory") or _NullMemory()
    bear_memory = ctx.artifacts.get("_bear_memory") or _NullMemory()
    rm_memory = ctx.artifacts.get("_invest_judge_memory") or _NullMemory()

    # 创建 Bull/Bear 节点
    bull_fn = create_bull_researcher(ctx.llm, bull_memory, min_rounds, max_rounds)
    bear_fn = create_bear_researcher(ctx.llm, bear_memory, min_rounds, max_rounds)

    # 🆕 独立的 used_skills 池（P1 修复）
    used_skills_bull: dict = {}
    used_skills_bear: dict = {}

    max_iter = max_rounds + 3
    print(f"\n   🧠 [research_team] starting debate: min={min_rounds} max={max_rounds}")

    for round_idx in range(max_iter):
        # 🆕 每轮开头压缩 history
        debate_state = _compress_debate_history(debate_state)

        # ===== Bull 回合 =====
        bull_input = {
            **ctx.artifacts,
            "investment_debate_state": debate_state,
            "used_skills": used_skills_bull,    # 🆕 传 Bull 独立池
        }
        bull_result = bull_fn(bull_input)
        debate_state = bull_result["investment_debate_state"]
        used_skills_bull = bull_result.get("used_skills", used_skills_bull)   # 🆕 接住更新
        print(f"   🐂 [research_team] Bull done: current_round={debate_state.get('current_round')}, "
              f"used_skills_bull={len(used_skills_bull)}")

        # should_continue_bull：只做安全保护
        round_num = debate_state.get("current_round", 1)
        if round_num > max_rounds:
            debate_state["stop_reason"] = "max_rounds_reached"
            print(f"   🛑 [research_team] stop after Bull: max_rounds_reached")
            break

        # ===== Bear 回合 =====
        bear_input = {
            **ctx.artifacts,
            "investment_debate_state": debate_state,
            "used_skills": used_skills_bear,    # 🆕 传 Bear 独立池
        }
        bear_result = bear_fn(bear_input)
        debate_state = bear_result["investment_debate_state"]
        used_skills_bear = bear_result.get("used_skills", used_skills_bear)   # 🆕 接住更新

        # should_continue_bear 三档判据
        round_num = debate_state.get("current_round", 1)
        completed = round_num - 1
        print(f"   🐻 [research_team] Bear done: completed_rounds={completed}, "
              f"used_skills_bear={len(used_skills_bear)}, "
              f"streak={debate_state.get('no_new_points_streak', 0)}")

        if completed < min_rounds:
            continue
        if completed >= max_rounds:
            debate_state["stop_reason"] = "max_rounds_reached"
            print(f"   🛑 [research_team] stop: max_rounds_reached ({completed} rounds)")
            break
        if debate_state.get("no_new_points_streak", 0) >= 1:
            debate_state["stop_reason"] = "argument_space_exhausted"
            print(f"   🛑 [research_team] stop: argument_space_exhausted")
            break

    # ===== Research Manager 最终裁决 =====
    # LLM 优先 deep（如通过 ctx.config["_deep_llm"] 注入），否则用 ctx.llm
    rm_llm = cfg.get("_deep_llm") or ctx.llm
    rm_fn = create_research_manager(rm_llm, rm_memory)
    rm_input = {
        **ctx.artifacts,
        "investment_debate_state": debate_state,
    }
    rm_result = rm_fn(rm_input)
    investment_plan = rm_result.get("investment_plan", "")

    final_history_len = len(debate_state.get("history", ""))
    print(f"   🧠 [research_team] done: rounds={debate_state['count'] // 2} "
          f"history_len={final_history_len} "
          f"stop_reason={debate_state.get('stop_reason', 'N/A')}")

    return SkillResult(
        outputs={
            "investment_debate_state": debate_state,
            "investment_plan": investment_plan,
            # ❌ 不返回 messages（避免污染 graph state）
        },
        metadata={
            "agent": "research_team",
            "rounds": debate_state["count"] // 2,
            "stop_reason": debate_state.get("stop_reason", ""),
            "history_len": final_history_len,
            "used_skills_bull_count": len(used_skills_bull),
            "used_skills_bear_count": len(used_skills_bear),
        },
    )
