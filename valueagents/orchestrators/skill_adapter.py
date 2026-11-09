# valueagents/orchestrators/skill_adapter.py
"""
SkillAdapter — 统一调用 master skill（19 个）和 core skill（9 个）。

接口差异：
  - master：tool.func(ticker=..., end_date=..., api_key=...) -> JSON str
  - core  ：skill.execute(ctx: SkillContext) -> SkillResult(outputs dict)

输出格式统一为 dict，由 Orchestrator merge 进 ArtifactStore。

输出 key 约定：
  - master skill：{name}_signal / {name}_confidence / {name}_reasoning
  - core skill  ：直接透传 SkillResult.outputs（如 market_report）
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from valueagents.agents.skills.contract import SkillContext
from valueagents.agents.skills.runtime import set_current_llm, reset_current_llm

from .skill_catalog import SkillCatalog


class SkillAdapter:
    """统一调用 master / core skill，屏蔽接口差异。"""

    MASTER_SIGNAL_SUFFIX = "_signal"
    MASTER_CONFIDENCE_SUFFIX = "_confidence"
    MASTER_REASONING_SUFFIX = "_reasoning"
    MASTER_REASONING_MAX = 500   # 完整 reasoning 可能几千字，截断进 artifact

    def __init__(
        self,
        registry: Any,
        llm: Any,
        config: dict,
        artifact_store: Any,
        memory_bag: Optional[dict] = None,
    ):
        """
        Args:
            registry: 19 个 master skill 的 registry（get_registry()）
            llm: 主 LLM 实例（带 callbacks）
            config: orchestrator 配置（含 min_debate_rounds 等）
            artifact_store: ArtifactStore 实例（用于读写 artifacts / 缓存）
            memory_bag: {_bull_memory: ..., _bear_memory: ...}，注入到 core skill 的 ctx.artifacts
        """
        self.registry = registry
        self.llm = llm
        self.config = config
        self.artifact = artifact_store
        self.memory_bag = memory_bag or {}

    # ============================================================
    # 统一入口
    # ============================================================
    def invoke(
        self,
        skill_name: str,
        args: Optional[dict] = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """调用 skill，返回 outputs dict（不 merge 到 store）。

        Args:
            skill_name: skill 名（如 "warren_buffett_analyst" / "market_analyst"）
            args: master skill 的额外参数（ticker / end_date / api_key），core skill 忽略
            use_cache: 是否启用缓存（同 skill + 同 args 只跑一次）

        Returns:
            dict[str, Any]，可直接传给 ArtifactStore.merge()
        """
        args = args or {}
        cache_args = self._cache_args(args)

        if use_cache:
            cached = self.artifact.cache_get(skill_name, cache_args)
            if cached is not None:
                print(f"   [Adapter] {skill_name}  CACHE HIT")
                return cached

        kind = SkillCatalog.kind(skill_name)
        if kind == "master":
            outputs = self._invoke_master(skill_name, args)
        else:
            outputs = self._invoke_core(skill_name)

        if use_cache and outputs:
            self.artifact.cache_put(skill_name, cache_args, outputs)

        return outputs

    # ============================================================
    # master skill
    # ============================================================
    def _invoke_master(self, skill_name: str, args: dict) -> dict[str, Any]:
        """调用 19 个大师 skill，输出拆为 3 个原始类型 key。"""
        ticker = args.get("ticker", self.artifact.ticker)
        end_date = args.get("end_date", self.artifact.end_date)
        api_key = args.get("api_key")

        tool = self.registry.get_tool(skill_name)
        if tool is None:
            raise ValueError(f"Master skill not found in registry: {skill_name}")

        print(f"   [Adapter] invoking master skill: {skill_name} (ticker={ticker})")

        token = set_current_llm(self.llm)
        try:
            raw = tool.func(ticker=ticker, end_date=end_date, api_key=api_key)
        except Exception as e:
            print(f"   [Adapter] ❌ {skill_name} raised: {type(e).__name__}: {e}")
            parsed = {
                "signal": "neutral",
                "confidence": 0,
                "reasoning": f"Skill invocation failed: {e}",
            }
            return self._wrap_master_output(skill_name, parsed)
        finally:
            reset_current_llm(token)

        parsed = self._parse_master_output(raw, skill_name)
        return self._wrap_master_output(skill_name, parsed)

    def _parse_master_output(self, raw: Any, skill_name: str) -> dict[str, Any]:
        """master skill 返回 JSON str，解析为 {signal, confidence, reasoning}。"""
        if isinstance(raw, dict):
            data = raw
        elif isinstance(raw, str):
            data = self._try_parse_json(raw)
        else:
            data = None

        if not isinstance(data, dict):
            return {
                "signal": "neutral",
                "confidence": 0,
                "reasoning": f"Unparseable output from {skill_name}: {str(raw)[:200]}",
            }

        return {
            "signal": str(data.get("signal", "neutral")).lower(),
            "confidence": float(data.get("confidence", 0) or 0),
            "reasoning": str(data.get("reasoning", ""))[: self.MASTER_REASONING_MAX],
        }

    @staticmethod
    def _try_parse_json(text: str) -> Optional[dict]:
        """尝试解析 JSON，容忍 markdown 包裹。"""
        text = text.strip()

        # 1) 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2) ```json ... ``` 包裹
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 3) 找第一个 { ... } 大括号平衡块
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    def _wrap_master_output(self, skill_name: str, parsed: dict[str, Any]) -> dict[str, Any]:
        """把 {signal, confidence, reasoning} 拆成 3 个原始类型 key。"""
        return {
            f"{skill_name}{self.MASTER_SIGNAL_SUFFIX}": parsed["signal"],
            f"{skill_name}{self.MASTER_CONFIDENCE_SUFFIX}": parsed["confidence"],
            f"{skill_name}{self.MASTER_REASONING_SUFFIX}": parsed["reasoning"],
        }

    # ============================================================
    # core skill
    # ============================================================
    def _invoke_core(self, skill_name: str) -> dict[str, Any]:
        """调用 9 个 core skill，透传 SkillResult.outputs。"""
        # 延迟 import，避免启动时循环
        from valueagents.agents.skills.core import load_core_skill

        skill = load_core_skill(f"{skill_name}_skill") or load_core_skill(skill_name)
        if skill is None:
            raise ValueError(f"Core skill not found: {skill_name}")

        print(f"   [Adapter] invoking core skill: {skill_name}")

        # 构造 artifacts：store 内容 + memory_bag
        artifacts = self.artifact.to_dict()
        artifacts.update(self.memory_bag)

        # 🆕 core skill 内部读 state["company_of_interest"] / state["trade_date"]
        artifacts["company_of_interest"] = self.artifact.ticker
        artifacts["trade_date"] = self.artifact.end_date

        ctx = SkillContext(
            ticker=self.artifact.ticker,
            end_date=self.artifact.end_date,
            artifacts=artifacts,
            llm=self.llm,
            api_key=self.config.get("api_key"),
            config={
                "min_debate_rounds": self.config.get("min_debate_rounds", 1),
                "max_debate_rounds": self.config.get("max_debate_rounds", 5),
                "max_risk_discuss_rounds": self.config.get("max_risk_discuss_rounds", 1),
                "master_analysts": self.config.get("master_analysts", []), 
            },
        )

        token = set_current_llm(self.llm)
        try:
            result = skill.execute(ctx)
        except Exception as e:
            print(f"   [Adapter] ❌ {skill_name} raised: {type(e).__name__}: {e}")
            return {}   # 让 orchestrator 决定如何处理（通常是报告给 LLM）
        finally:
            reset_current_llm(token)

        # SkillResult.outputs 是 dict，直接返回
        outputs = dict(result.outputs) if result and result.outputs else {}
        print(f"   [Adapter] {skill_name} done. outputs keys: {list(outputs.keys())}")
        return outputs

    # ============================================================
    # 辅助
    # ============================================================
    @staticmethod
    def _cache_args(args: dict) -> dict:
        """从 args 里剔除敏感字段（api_key），作为缓存 key 的输入。"""
        return {k: v for k, v in args.items() if k != "api_key"}
