# valueagents/agents/utils/error_contract.py
"""数据不可用时的统一错误契约。

所有 tool 在"数据源全失败 + 缓存为空"时返回这个前缀，
让 LLM 和下游可以识别并停止编造。

设计原则：
  - 前缀必须唯一且不易出现在正常文本里
  - LLM 侧有明确约定（INSUFFICIENT_DATA）
  - 下游（skill / regression）可以字符串匹配
"""

DATA_UNAVAILABLE_PREFIX = "[DATA_UNAVAILABLE]"
PARTIAL_DATA_PREFIX = "[PARTIAL_DATA]"

# LLM 报告里的识别标记
INSUFFICIENT_DATA_MARKER = "INSUFFICIENT_DATA"

# 报告长度上限（数据全失败时）
INSUFFICIENT_REPORT_MAX_WORDS = 200


def data_unavailable(role: str, reason: str) -> str:
    """生成"数据不可用"的标准返回。

    Args:
        role: 人类可读的用途，如 "company news for NFLX"
        reason: 失败原因，如 "all sources timed out"

    Returns:
        给 LLM 看的 tool 结果。LLM 看到前缀后应按 prompt 约定停止。
    """
    return (
        f"{DATA_UNAVAILABLE_PREFIX} role={role} reason={reason}\n"
        f"\n"
        f"INSTRUCTION: Do NOT fabricate data. Do NOT write speculative analysis. "
        f"Do NOT add tables or hypothetical scenarios. "
        f"Respond with a report under {INSUFFICIENT_REPORT_MAX_WORDS} words that:\n"
        f"  1. Starts with the exact marker `{INSUFFICIENT_DATA_MARKER}: <short reason>`\n"
        f"  2. Explains which data is missing\n"
        f"  3. Stops."
    )


def partial_data(role: str, got: int, total: int) -> str:
    """生成"部分数据可用"的标准返回。"""
    return (
        f"{PARTIAL_DATA_PREFIX} role={role} got={got}/{total}\n"
        f"INSTRUCTION: Continue the analysis with available data, "
        f"but explicitly state what is missing in a short 'Data Gaps' note."
    )


def is_data_unavailable(text: str) -> bool:
    """判断 tool 返回是否是"数据不可用"。"""
    return bool(text) and text.startswith(DATA_UNAVAILABLE_PREFIX)


def is_partial_data(text: str) -> bool:
    return bool(text) and text.startswith(PARTIAL_DATA_PREFIX)


def report_marks_insufficient(report: str) -> bool:
    """判断 LLM 报告是否按约定标注了 INSUFFICIENT_DATA。"""
    if not report:
        return False
    head = report[:300]
    return INSUFFICIENT_DATA_MARKER in head
