# valueagents/agents/utils/context_compressor.py
"""
4 层递进压缩器，适配 LangGraph tool 层。

Layer 1（规则门控）：无效检测 / 短文本 / 超长卸载
Layer 2（阈值触发）：累计 token 预算达到 80% 才压
Layer 3（上下文感知）：两阶段 LLM 压缩 + query_reason + context
Layer 4（断路器 + 兜底）：连续失败停止重试，本地截断
"""

from dataclasses import dataclass, field
from typing import Optional
import hashlib
import os

from valueagents.agents.utils.compress_utils import (
    compress_text,          # 复用现有的两阶段 LLM 压缩
    estimate_word_count,
    safe_truncate,
)

_OFFLOAD_DIR = "offloaded"
_INVALID_RATIO_THRESHOLD = 0.30
_SHORT_TEXT_WORDS = 150
_OFFLOAD_CHARS = 20000
_BUDGET_RATIO = 0.80
_MAX_CONSECUTIVE_FAILURES = 3


@dataclass
class CompressionState:
    """每个 analyst 节点维护一份，跨 tool 调用累积。"""
    token_budget: int = 80000
    consumed_tokens: int = 0
    recent_summaries: list = field(default_factory=list)   # 最近 3 条压缩结果，作为 context
    consecutive_failures: int = 0
    stats: dict = field(default_factory=lambda: {
        "L1_skipped": 0, "L1_offloaded": 0,
        "L2_deferred": 0, "L3_compressed": 0,
        "L4_fallback": 0, "L4_circuit_open": 0,
    })

    def over_threshold(self, incoming_tokens: int) -> bool:
        return (self.consumed_tokens + incoming_tokens) > self.token_budget * _BUDGET_RATIO

    def record_summary(self, summary: str):
        self.recent_summaries.append(summary[:300])
        self.recent_summaries = self.recent_summaries[-3:]

    def get_context(self) -> str:
        if not self.recent_summaries:
            return "None"
        return "\n---\n".join(self.recent_summaries)


def _estimate_tokens(text: str) -> int:
    """粗估 token 数：英文约 1.3 token/word，中英文混合保守取 2x。"""
    return int(estimate_word_count(text) * 2.0)


def _is_invalid(text: str) -> bool:
    """L1 门控：无效数据检测。"""
    na_count = text.count("N/A") + text.count("None") + text.count("No data")
    return na_count > len(text) * _INVALID_RATIO_THRESHOLD


def _is_short(text: str) -> bool:
    """L1 门控：短文本不压缩。"""
    return estimate_word_count(text) < _SHORT_TEXT_WORDS


def _should_offload(text: str) -> bool:
    """L1 门控：超长文本卸载到文件。"""
    return len(text) > _OFFLOAD_CHARS


def _offload_to_file(text: str, role: str) -> str:
    """L1 卸载：写入文件，返回指针。"""
    os.makedirs(_OFFLOAD_DIR, exist_ok=True)
    h = hashlib.md5(text.encode()).hexdigest()[:12]
    path = os.path.join(_OFFLOAD_DIR, f"{h}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return f"[Data offloaded to {path} ({len(text)} chars). Use read_file tool to access.]"


# ========== 全局 CompressionState 管理 ==========
_global_state: Optional[CompressionState] = None
_global_agent: Optional[str] = None

def reset_global_state(token_budget: int = 30000, agent_name: Optional[str] = None) -> CompressionState:
    """
    每个节点开头调用。
    - agent_name 相同：tool loop 的重复进入，不 reset（保留 tool 阶段累积的 stats）
    - agent_name 不同或 None：新的 agent，reset
    """
    global _global_state, _global_agent
    if agent_name is not None and _global_agent == agent_name and _global_state is not None:
        # 同一个 agent 的 tool loop 回环，保留 stats
        return _global_state
    _global_state = CompressionState(token_budget=token_budget)
    _global_agent = agent_name
    return _global_state

def get_global_state() -> Optional[CompressionState]:
    return _global_state

def report_global_state(agent_name: str):
    """临时诊断：在节点末尾调用，打印分层统计。"""
    if _global_state is None:
        return
    s = _global_state.stats
    total = sum(s.values())
    if total == 0:
        return
    print(f"   [COMPRESSION_STATS][{agent_name}] "
          f"L1_skip={s['L1_skipped']} L1_offload={s['L1_offloaded']} "
          f"L2_defer={s['L2_deferred']} L3_compress={s['L3_compressed']} "
          f"L4_fallback={s['L4_fallback']} L4_circuit={s['L4_circuit_open']} "
          f"total={total} consumed={_global_state.consumed_tokens}/{_global_state.token_budget}")


def compress(
    text: str,
    role: str,
    max_words: int = 150,
    query_reason: str = "general analysis",
    state: Optional[CompressionState] = None,
    config: Optional[dict] = None,
) -> str:
    """
    4 层递进压缩入口。所有 tool 统一调用这个函数，不再直接调 compress_text。
    """
    if not text or len(text) < 100:
        return text

    if state is None:
        state = _global_state

    # ========== L1：规则门控（零 LLM） ==========
    if _is_invalid(text):
        if state: state.stats["L1_skipped"] += 1
        return f"No valid data available for: {role}"

    if _is_short(text):
        if state: state.stats["L1_skipped"] += 1
        return text

    if _should_offload(text):
        if state:
            state.stats["L1_offloaded"] += 1
            state.consumed_tokens += 200  # 指针约 200 token
        return _offload_to_file(text, role)

    # ========== L2：阈值触发（零 LLM） ==========
    incoming_tokens = _estimate_tokens(text)
    if state and not state.over_threshold(incoming_tokens):
        state.stats["L2_deferred"] += 1
        state.consumed_tokens += incoming_tokens
        return text   # 预算没满，不压缩，直接放行

    # ========== L4 前置：断路器 ==========
    if state and state.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        state.stats["L4_circuit_open"] += 1
        return safe_truncate(text, max_chars=max_words * 4)

    # ========== L3：上下文感知 LLM 压缩 ==========
    try:
        summary = compress_text(
            text=text,
            max_words=max_words,
            role=role,
            query_reason=query_reason,
            context=state.get_context() if state else None,
            config=config,
        )
        if state:
            state.stats["L3_compressed"] += 1
            state.consecutive_failures = 0
            state.consumed_tokens += _estimate_tokens(summary)
            state.record_summary(summary)
        return summary
    except Exception as e:
        # ========== L4：兜底 ==========
        if state:
            state.stats["L4_fallback"] += 1
            state.consecutive_failures += 1
        print(f"   ⚠️ [CONTEXT_COMPRESSOR] L3 failed, falling back: {e}")
        return safe_truncate(text, max_chars=max_words * 4)
