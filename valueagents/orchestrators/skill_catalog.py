# valueagents/orchestrators/skill_catalog.py
"""
SkillCatalog — Orchestrator 用的 skill 元数据目录。

3 类 skill：
  - master（19 个）：从 SkillRegistry 动态读，不写入 artifact（返回 signal）
  - leaf（7 个）：4 analyst + trader + research_manager + portfolio_manager
  - meta（2 个）：research_team / risk_team（内部组合多个 skill）

设计原则：
  - 9 个 core skill 的 requires / produces 是业务定义，硬编码在 catalog 里
  - 19 个 master skill 只从 registry 动态读名字 / description，不硬编码
  - requires / produces 是"业务契约"，不依赖 skill 实际实现（skill 内部改了不影响 catalog）
"""

from __future__ import annotations

from typing import Any, Optional


# ============================================================
# Core skill 元数据（9 个，硬编码）
# ============================================================
# 格式：name → {"kind", "requires", "produces", "description"}
#   - requires: 调用前必须已存在于 artifact 的 key
#   - produces: 调用后写入 artifact 的 key
_CORE_SKILLS: dict[str, dict[str, Any]] = {
    # --- 4 个 analyst（leaf，无依赖） ---
    "market_analyst": {
        "kind": "leaf",
        "requires": [],
        "produces": ["market_report"],
        "description": "Technical analysis with up to 8 indicators, produces market_report",
    },
    "social_analyst": {
        "kind": "leaf",
        "requires": [],
        "produces": ["sentiment_report"],
        "description": "Social media & company-specific news sentiment, produces sentiment_report",
    },
    "news_analyst": {
        "kind": "leaf",
        "requires": [],
        "produces": ["news_report"],
        "description": "Company news + global macro news, produces news_report",
    },
    "fundamentals_analyst": {
        "kind": "leaf",
        "requires": [],
        "produces": ["fundamentals_report"],
        "description": "Financial statements & company overview, produces fundamentals_report",
    },

    # --- trader（leaf，依赖 investment_plan + 4 report） ---
    "trader": {
        "kind": "leaf",
        "requires": ["market_report", "sentiment_report", "news_report",
                     "fundamentals_report", "investment_plan"],
        "produces": ["trader_investment_plan"],
        "description": "Translates investment_plan into a concrete BUY/HOLD/SELL trade plan",
    },

    # --- research_manager（leaf，依赖 4 report + debate_state） ---
    "research_manager": {
        "kind": "leaf",
        "requires": ["market_report", "sentiment_report", "news_report",
                     "fundamentals_report", "investment_debate_state"],
        "produces": ["investment_plan"],
        "description": "Synthesizes Bull/Bear debate into investment_plan",
    },

    # --- portfolio_manager（leaf，依赖最深） ---
    "portfolio_manager": {
        "kind": "leaf",
        "requires": ["market_report", "sentiment_report", "news_report",
                     "fundamentals_report", "investment_plan",
                     "trader_investment_plan", "risk_debate_state"],
        "produces": ["final_trade_decision"],
        "description": "Synthesizes risk debate into final BUY/HOLD/SELL decision",
    },

    # --- research_team（meta，内部跑 Bull↔Bear + RM） ---
    "research_team": {
        "kind": "meta",
        "requires": ["market_report", "sentiment_report", "news_report",
                     "fundamentals_report"],
        "produces": ["investment_debate_state", "investment_plan"],
        "description": "Runs Bull/Bear debate + Research Manager synthesis (3-in-1)",
    },

    # --- risk_team（meta，内部跑 3 debator） ---
    "risk_team": {
        "kind": "meta",
        "requires": ["market_report", "sentiment_report", "news_report",
                     "fundamentals_report", "trader_investment_plan"],
        "produces": ["risk_debate_state"],
        "description": "Runs 3-way risk debate (Aggressive/Conservative/Neutral)",
    },
    # 🆕 Phase 6a
    "master_team": {
        "kind": "meta",
        "requires": ["market_report", "sentiment_report", "news_report", "fundamentals_report"],
        "produces": ["master_analyst_signals", "master_summary"],
        "description": "Runs N selected master analysts (Buffett/Munger/Graham/...) and aggregates signals",
    },
}


# ============================================================
# 已知的 19 个 master skill 名字（硬编码，作为 source of truth + 启动校验）
# ============================================================
# 这些名字与 skills/{xxx}_skill/SKILL.md 的 `name:` 字段一致
_KNOWN_MASTER_SKILLS: set[str] = {
    "ben_graham_analyst",
    "warren_buffett_analyst",
    "charlie_munger_analyst",
    "peter_lynch_analyst",
    "phil_fisher_analyst",
    "bill_ackman_analyst",
    "michael_burry_analyst",
    "aswath_damodaran_analyst",
    "mohnish_pabrai_analyst",
    "nassim_taleb_analyst",
    "cathie_wood_analyst",
    "stanley_druckenmiller_analyst",
    "rakesh_jhunjhunwala_analyst",
    "fundamental_analyst",
    "growth_analyst",
    "news_sentiment_analyst",
    "sentiment_analyst",
    "technical_analyst",
    "valuation_analyst",
}


class SkillCatalog:
    """Orchestrator 的 skill 元数据目录。"""

    # ---------------- 基础分类 ----------------
    @classmethod
    def is_core(cls, name: str) -> bool:
        return name in _CORE_SKILLS

    @classmethod
    def is_master(cls, name: str) -> bool:
        """已知的 19 个 → True；未知名字 → False（靠 registry 兜底，见 kind）。"""
        return name in _KNOWN_MASTER_SKILLS

    @classmethod
    def kind(cls, name: str) -> str:
        """返回 "leaf" / "meta" / "master"。未知 skill 抛 KeyError。"""
        if name in _CORE_SKILLS:
            return _CORE_SKILLS[name]["kind"]
        if name in _KNOWN_MASTER_SKILLS:
            return "master"
        # 未知名字 → 尝试从 registry 动态判断
        try:
            from valueagents.agents.skills.registry import get_registry
            if name in get_registry():
                return "master"
        except Exception:
            pass
        raise KeyError(f"Unknown skill: {name!r}")

    # ---------------- requires / produces ----------------
    @classmethod
    def requires(cls, name: str) -> list[str]:
        """调用前必须存在的 artifact key 列表。master skill 返回 []。"""
        if name in _CORE_SKILLS:
            return list(_CORE_SKILLS[name]["requires"])
        return []   # master skill 只依赖 ticker/end_date

    @classmethod
    def produces(cls, name: str) -> list[str]:
        """调用后写入 artifact 的 key 列表。master skill 返回 []（不写 artifact）。"""
        if name in _CORE_SKILLS:
            return list(_CORE_SKILLS[name]["produces"])
        return []

    # ---------------- 前置校验 ----------------
    @classmethod
    def check_requires(cls, name: str, artifact_store) -> tuple[bool, list[str]]:
        """检查 artifact 是否满足 skill 的 requires。

        Returns:
            (ok, missing_keys)
        """
        missing = [k for k in cls.requires(name) if not artifact_store.has(k)]
        return (len(missing) == 0, missing)

    # ---------------- description ----------------
    @classmethod
    def description(cls, name: str, max_chars: int = 200) -> str:
        """返回 skill 的一句话描述。"""
        if name in _CORE_SKILLS:
            desc = _CORE_SKILLS[name]["description"]
        else:
            # master skill：从 registry 读 tool.description
            try:
                from valueagents.agents.skills.registry import get_registry
                tool = get_registry().get_tool(name)
                desc = (tool.description if tool else "") or ""
            except Exception:
                desc = ""
        return desc[:max_chars]

    # ---------------- 全量枚举 ----------------
    @classmethod
    def core_skill_names(cls) -> list[str]:
        return list(_CORE_SKILLS.keys())

    @classmethod
    def master_skill_names(cls) -> list[str]:
        return sorted(_KNOWN_MASTER_SKILLS)

    @classmethod
    def all_skill_names(cls) -> list[str]:
        return cls.core_skill_names() + cls.master_skill_names()

    @classmethod
    def all_skills(cls, include_master: bool = True) -> list[dict[str, Any]]:
        """给 prompts.py 用的 skill 列表（含 description / requires / produces）。

        Args:
            include_master: 是否包含 19 个 master skill（prompt 会很长）

        Returns:
            [{"name", "kind", "description", "requires", "produces"}, ...]
        """
        result: list[dict[str, Any]] = []

        # core skills（9 个）
        for name, meta in _CORE_SKILLS.items():
            result.append({
                "name": name,
                "kind": meta["kind"],
                "description": meta["description"],
                "requires": list(meta["requires"]),
                "produces": list(meta["produces"]),
            })

        # master skills（19 个）
        if include_master:
            for name in cls.master_skill_names():
                result.append({
                    "name": name,
                    "kind": "master",
                    "description": cls.description(name),
                    "requires": [],
                    "produces": [],
                })

        return result

    # ---------------- 启动校验（诊断） ----------------
    @classmethod
    def validate_against_registry(cls) -> dict[str, Any]:
        """启动时校验：_KNOWN_MASTER_SKILLS 与 registry 是否一致。

        用于发现"新增 skill 但忘更新 _KNOWN_MASTER_SKILLS"或"删了 skill 但 catalog 还留着"。
        """
        try:
            from valueagents.agents.skills.registry import get_registry
            registry_names = set(get_registry().names())
        except Exception as e:
            return {"ok": False, "error": str(e)}

        known = _KNOWN_MASTER_SKILLS
        missing_in_catalog = registry_names - known   # registry 有但 catalog 没列
        missing_in_registry = known - registry_names  # catalog 列了但 registry 没有

        return {
            "ok": not missing_in_catalog and not missing_in_registry,
            "registry_count": len(registry_names),
            "catalog_count": len(known),
            "missing_in_catalog": sorted(missing_in_catalog),
            "missing_in_registry": sorted(missing_in_registry),
        }
