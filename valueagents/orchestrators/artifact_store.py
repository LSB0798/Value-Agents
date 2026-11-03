# valueagents/orchestrators/artifact_store.py
"""
ArtifactStore — 对话式编排器的中间产物黑板。

职责：
  - 持有 ticker / end_date / artifacts（skill 的产物）
  - merge: 把 skill outputs 合并进来（过滤内部字段、空值）
  - get / has / keys: 只读访问
  - summary: 给 LLM 看的摘要（类型感知截断，防 prompt 膨胀）
  - cache: 同一 skill 同一 args 缓存结果，避免重复调用

不持有：
  - messages（会无限膨胀，不能进 artifact）
  - memory 对象（AgentState 字段，不属于产物）
  - _config / used_skills / sender（内部状态）
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


# 不进入 artifact 的字段（中间过程 / 会无限膨胀 / 非产物）
_EXCLUDE_KEYS: set[str] = {
    # LangChain 消息列表：会无限累积
    "messages",
    # 运行时配置
    "_config",
    # memory 对象（阶段 4a 引入）
    "_bull_memory",
    "_bear_memory",
    "_trader_memory",
    "_invest_judge_memory",
    "_portfolio_manager_memory",
    # bull/bear researcher 的内部字段
    "used_skills",
    "bull_conclusions",
    "bear_conclusions",
    "bull_tool_decision",
    "bear_tool_decision",
    # trader 的内部字段
    "sender",
}


class ArtifactStore:
    """对话式编排器的中间产物黑板。

    Usage:
        store = ArtifactStore("GOOGL", "2026-06-20")
        store.merge({"market_report": "..."})
        assert store.has("market_report")
        print(store.summary())
    """

    def __init__(self, ticker: str, end_date: str):
        self.ticker = ticker
        self.end_date = end_date
        self.artifacts: dict[str, Any] = {}
        # skill_name::args_hash -> outputs，防重复调用
        self._cache: dict[str, dict[str, Any]] = {}

    # ============================================================
    # 合并
    # ============================================================
    def merge(self, outputs: dict[str, Any]) -> dict[str, Any]:
        """把 skill outputs 合并到 artifacts。

        - 跳过 _EXCLUDE_KEYS 里的字段（内部状态 / 膨胀字段）
        - 跳过 None 和空串（避免 has() 误判为"已存在"）
        - 覆盖同名字段（后写入的赢，符合"最新结果"语义）

        Returns:
            实际写入的字段 dict（供诊断）
        """
        written: dict[str, Any] = {}
        for k, v in outputs.items():
            if k in _EXCLUDE_KEYS:
                continue
            if v is None or v == "":
                continue
            self.artifacts[k] = v
            written[k] = v
        return written

    # ============================================================
    # 只读访问
    # ============================================================
    def get(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def has(self, key: str) -> bool:
        """key 存在且值非空。"""
        return key in self.artifacts and self.artifacts[key] not in (None, "")

    def keys(self) -> list[str]:
        return sorted(self.artifacts.keys())

    def to_dict(self) -> dict[str, Any]:
        """浅拷贝，供 SkillContext.artifacts 使用。"""
        return dict(self.artifacts)

    def clear(self) -> None:
        self.artifacts.clear()
        self._cache.clear()

    def __len__(self) -> int:
        return len(self.artifacts)

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __repr__(self) -> str:
        return f"ArtifactStore(ticker={self.ticker!r}, date={self.end_date!r}, keys={self.keys()})"

    # ============================================================
    # 调用缓存：同一 skill 同一 args 不重复跑
    # ============================================================
    @staticmethod
    def _cache_key(skill_name: str, args: dict[str, Any]) -> str:
        try:
            args_str = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
        except Exception:
            args_str = str(sorted(args.items()))
        h = hashlib.md5(args_str.encode()).hexdigest()[:12]
        return f"{skill_name}::{h}"

    def cache_get(self, skill_name: str, args: dict[str, Any]) -> Optional[dict[str, Any]]:
        return self._cache.get(self._cache_key(skill_name, args))

    def cache_put(self, skill_name: str, args: dict[str, Any], outputs: dict[str, Any]) -> None:
        self._cache[self._cache_key(skill_name, args)] = dict(outputs)

    def cache_size(self) -> int:
        return len(self._cache)

    # ============================================================
    # 摘要（给 LLM 看）
    # ============================================================
    def summary(self, max_chars: int = 2000, per_key_chars: int = 300) -> str:
        """给 LLM 看的 artifacts 摘要。

        - str 值：单行化后截断到 per_key_chars
        - dict 值：只显示 keys（不展开内容）
        - list 值：只显示长度
        - 整体超过 max_chars 再截断

        Returns:
            多行文本，每行形如 `- market_report: All indicator data ...`
            空 store 返回 `(empty)`
        """
        if not self.artifacts:
            return "(empty)"

        lines: list[str] = []
        for k in self.keys():
            v = self.artifacts[k]
            lines.append(f"- {k}: {self._format_value(v, per_key_chars)}")

        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        return text

    @staticmethod
    def _format_value(v: Any, limit: int) -> str:
        if isinstance(v, str):
            s = v.replace("\n", " ").strip()
            return s if len(s) <= limit else s[: limit - 3] + "..."
        if isinstance(v, dict):
            keys = list(v.keys())
            shown = keys[:8]
            extra = "..." if len(keys) > 8 else ""
            return f"<dict keys={shown}{extra}>"
        if isinstance(v, list):
            return f"<list len={len(v)}>"
        return repr(v)[:limit]

    # ============================================================
    # 诊断
    # ============================================================
    def stats(self) -> dict[str, Any]:
        """给调试用：各 key 的字符数 / 类型。"""
        return {
            k: {
                "type": type(v).__name__,
                "size": len(v) if hasattr(v, "__len__") else None,
            }
            for k, v in self.artifacts.items()
        }
