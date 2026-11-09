---
name: trader
kind: core
description: "Translates the research investment plan into a concrete trading recommendation (BUY/HOLD/SELL) with the mandatory 'FINAL TRANSACTION PROPOSAL' line for downstream signal extraction."
requires:
  - market_report
  - sentiment_report
  - news_report
  - fundamentals_report
  - investment_plan
produces:
  - trader_investment_plan
  - messages
  - sender
capabilities:
  - trade_decision
  - entry_exit_recommendation
  - final_proposal_tagging
best_for:
  - 将研究计划落地为可执行交易
  - 输出 BUY/HOLD/SELL 明确立场
  - 供 portfolio_manager 二次裁决的输入
not_for:
  - 替代研究裁决（research_manager 负责）
  - 风险辩论（risk_team 负责）
  - 独立基本面/技术面分析
---

# Trader Skill

将研究经理的 investment plan 转化为具体交易建议，必须以
`FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**` 结尾，供 `SignalProcessor` 提取最终信号。

## Inputs

- `company_of_interest`（必填）：股票代码
- `market_report` / `sentiment_report` / `news_report` / `fundamentals_report`（必填）：4 份分析师报告（用于 `memory.get_memories` 检索相似情境）
- `investment_plan`（必填）：研究经理的裁决
- `_trader_memory`（可选）：`FinancialSituationMemory`，缺失时用 `_NullMemory` 兜底

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `trader_investment_plan` | `str` | 交易计划文本，**必须**含 `FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**` |
| `messages` | `List[BaseMessage]` | 单条 AI 消息（对齐老行为） |
| `sender` | `str` | 固定 `"Trader"` |

## Workflow

1. 从 `memory.get_memories(...)` 读取历史相似情境的教训（缺失时跳过）
2. 综合 investment_plan + 4 份 report，形成交易建议
3. 输出纯文本（不含 XML 标签），以 `FINAL TRANSACTION PROPOSAL: **<BUY/HOLD/SELL>**` 结尾
4. 保持对话式语气

## Notes

- **无 tool loop**：单次 `llm.invoke`，无 bind_tools
- **memory 可选**：第 1 期用 `_NullMemory` 兜底；第 2 期通过 `ctx.artifacts["_trader_memory"]` 注入
- **`create_trader` 返回 `functools.partial`**：`name="Trader"` 已被绑定，skill 里直接 `agent_node(state)` 调用
- **LLM 用 quick_think**：`setup.py` 传 `self.quick_thinking_llm`
- **`sender` 字段透传**：`AgentState` 未声明，但老代码一直返回，LangGraph 容忍（最终状态 `_log_state` 不写它，无害）
- **`messages` 会走 `operator.add` reducer**：老代码每轮返回 `[result]`，state 里 messages 会累积；skill 化后保持同样行为，保证最终 `state["messages"]` 与改造前一致
