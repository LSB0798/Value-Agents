# valueagents/orchestrators/conversational.py
"""
ConversationalOrchestrator — 对话式 skill 调度的主循环。

核心流程：
  1. 渲染 system prompt（含 skills 列表 + artifacts 摘要）
  2. LLM 返回 JSON：{"action": "call"/"done", ...}
  3. 前置校验（requires）
  4. 调 skill → 更新 artifacts → 反馈给 LLM
  5. 重复直到 done / max_steps / 连续解析失败

5 种分支全部处理，任何异常都不会让 orchestrator 崩溃。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .artifact_store import ArtifactStore
from .prompts import (
    render_system_prompt,
    render_feedback_message,
    render_rejection_message,
    render_error_message,
)
from .skill_adapter import SkillAdapter
from .skill_catalog import SkillCatalog
from valueagents.agents.utils.context_compressor import clear_global_state


class ConversationalOrchestrator:
    """LLM 驱动的 skill 调度器。

    Usage:
        orch = ConversationalOrchestrator(registry, llm, config)
        answer = orch.run("只跑 Buffett 看看", "GOOGL", "2026-06-20")
    """

    MAX_PARSE_FAILURES = 3   # 连续解析失败上限，超过则强制退出

    def __init__(
        self,
        registry: Any,
        llm: Any,
        config: dict,
        max_steps: int = 20,
        memory_bag: Optional[dict] = None,
        include_master_in_prompt: bool = True,
        verbose: bool = True,
    ):
        """
        Args:
            registry: 19 个 master skill 的 registry
            llm: 主 LLM 实例（带 callbacks）
            config: 配置 dict（min_debate_rounds 等）
            max_steps: 单次 run 最多步数（默认 20，跑完整流程约 8 步）
            memory_bag: {_bull_memory: ..., ...}，传给 SkillAdapter
            include_master_in_prompt: 是否在 prompt 里列 19 个 master skill
            verbose: 是否打印进度日志
        """
        self.registry = registry
        self.llm = llm
        self.config = config
        self.max_steps = max_steps
        self.memory_bag = memory_bag or {}
        self.include_master_in_prompt = include_master_in_prompt
        self.verbose = verbose

    # ============================================================
    # 主入口
    # ============================================================
    def run(self, user_query: str, ticker: str, end_date: str) -> str:
        """执行一次对话式调度。

        Args:
            user_query: 用户自然语言请求（如"只跑 Buffett 看看"）
            ticker: 股票代码
            end_date: 分析日期 YYYY-MM-DD

        Returns:
            LLM 在 done 时的 answer，或错误信息
        """
        clear_global_state()
        store = ArtifactStore(ticker, end_date)
        adapter = SkillAdapter(
            registry=self.registry,
            llm=self.llm,
            config=self.config,
            artifact_store=store,
            memory_bag=self.memory_bag,
        )

        skills = SkillCatalog.all_skills(include_master=self.include_master_in_prompt)
        messages: list = [
            SystemMessage(content=render_system_prompt(
                skills=skills,
                artifacts_summary=store.summary(),
                ticker=ticker,
                end_date=end_date,
            )),
            HumanMessage(content=user_query),
        ]

        consecutive_parse_failures = 0

        for step in range(1, self.max_steps + 1):
            self._log(f"\n[Orchestrator] Step {step}/{self.max_steps}  "
                      f"(artifacts: {len(store)} keys)")

            # 每步重新渲染 system prompt（artifacts 变了）
            messages[0] = SystemMessage(content=render_system_prompt(
                skills=skills,
                artifacts_summary=store.summary(),
                ticker=ticker,
                end_date=end_date,
            ))

            # ---------- 调 LLM ----------
            try:
                response = self.llm.invoke(messages)
            except Exception as e:
                self._log(f"[Orchestrator] ❌ LLM invoke failed: {e}")
                return (f"Orchestrator error: LLM invocation failed ({e}). "
                        f"Artifacts collected: {store.keys()}")

            raw_content = self._extract_content(response)
            messages.append(AIMessage(content=raw_content))

            # ---------- 解析 JSON ----------
            action = self._parse_action(raw_content)
            if action is None:
                consecutive_parse_failures += 1
                self._log(f"[Orchestrator] ⚠️ parse failure #{consecutive_parse_failures}: "
                          f"{raw_content[:120]!r}")
                messages.append(HumanMessage(content=(
                    "Your previous response was not valid JSON. "
                    "Reply ONLY with one of:\n"
                    '{"action": "call", "skill": "<name>", "args": {}}\n'
                    '{"action": "done", "answer": "<text>"}\n'
                    "No markdown, no explanations."
                )))
                if consecutive_parse_failures >= self.MAX_PARSE_FAILURES:
                    self._log(f"[Orchestrator] ⛔ {self.MAX_PARSE_FAILURES} parse failures; aborting")
                    return (f"Orchestrator stopped: {self.MAX_PARSE_FAILURES} "
                            f"consecutive invalid JSON responses. "
                            f"Artifacts: {store.keys()}")
                continue
            consecutive_parse_failures = 0

            # ---------- 分支 1: done ----------
            if action["action"] == "done":
                answer = action.get("answer", "") or "(empty answer)"
                self._log(f"[Orchestrator] ✅ DONE (step {step})")
                return answer

            # ---------- 分支 2-4: call ----------
            skill_name = action.get("skill")
            if not skill_name:
                messages.append(HumanMessage(content=(
                    'Missing "skill" field in {"action": "call"}. '
                    'Please specify a skill name.'
                )))
                continue

            if not self._skill_exists(skill_name):
                self._log(f"[Orchestrator] ⚠️ unknown skill: {skill_name}")
                messages.append(HumanMessage(content=(
                    f'Unknown skill "{skill_name}". '
                    f'Available: {", ".join(SkillCatalog.all_skill_names()[:10])}...'
                )))
                continue

            # ---------- 分支 3: requires 缺失 ----------
            ok, missing = SkillCatalog.check_requires(skill_name, store)
            if not ok:
                self._log(f"[Orchestrator] ⛔ {skill_name} rejected: missing {missing}")
                messages.append(HumanMessage(content=render_rejection_message(
                    skill_name, missing, store.summary()
                )))
                continue

            # ---------- 调 skill ----------
            self._log(f"[Orchestrator] → calling {skill_name}")
            try:
                outputs = adapter.invoke(skill_name, args=action.get("args", {}))
            except Exception as e:
                self._log(f"[Orchestrator] ❌ {skill_name} raised: {type(e).__name__}: {e}")
                messages.append(HumanMessage(content=render_error_message(
                    skill_name, f"{type(e).__name__}: {e}"
                )))
                continue

            # ---------- 分支 4: skill 空输出 ----------
            if not outputs:
                self._log(f"[Orchestrator] ⚠️ {skill_name} returned empty outputs")
                messages.append(HumanMessage(content=render_error_message(
                    skill_name, "returned empty outputs (may have failed silently)"
                )))
                continue

            # ---------- 分支 2: 成功 ----------
            written = store.merge(outputs)
            self._log(f"[Orchestrator] ✅ {skill_name} produced: {list(written.keys())}")

            if not written:
                # outputs 全部被 _EXCLUDE_KEYS 过滤（如只返回 messages）
                messages.append(HumanMessage(content=(
                    f"Skill `{skill_name}` returned outputs, but none were stored "
                    f"(they were internal state, not artifacts). "
                    f"Consider whether this skill can help with the user's request."
                )))
                continue

            messages.append(HumanMessage(content=render_feedback_message(
                skill_name, list(written.keys()), store.summary()
            )))

        # ---------- max_steps 兜底 ----------
        self._log(f"[Orchestrator] ⚠️ max_steps ({self.max_steps}) reached")
        return (
            f"Reached maximum steps ({self.max_steps}). "
            f"Artifacts collected: {store.keys()}. "
            f"Please refine your query or start a new session."
        )

    # ============================================================
    # 内部辅助
    # ============================================================
    def _skill_exists(self, name: str) -> bool:
        try:
            SkillCatalog.kind(name)
            return True
        except KeyError:
            return False

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    @staticmethod
    def _extract_content(response: Any) -> str:
        """兼容 str / list[dict{type:'text'}] / AIMessage。"""
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return str(content)

    @classmethod
    def _parse_action(cls, content: str) -> Optional[dict]:
        """解析 LLM 的 JSON action，失败返回 None。"""
        data = cls._try_parse_json(content)
        if not isinstance(data, dict):
            return None
        action = data.get("action")
        if action not in ("call", "done"):
            return None
        return data

    @staticmethod
    def _try_parse_json(text: str) -> Optional[dict]:
        """三级兜底 JSON 解析（与 SkillAdapter 的解析逻辑一致）。"""
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

        # 3) 大括号平衡块
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
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return None
        return None
