---
name: research_manager
kind: core
description: "Synthesizes the Bull↔Bear debate into a decisive investment plan (Buy/Sell/Hold) with rationale and concrete strategic actions for the trader."
requires:
  - market_report
  - sentiment_report
  - news_report
  - fundamentals_report
  - investment_debate_state
produces:
  - investment_plan
  - investment_debate_state
capabilities:
  - debate_synthesis
  - bull_bear_arbitration
  - investment_plan_generation
best_for:
  - 多空辩论后做裁决
  - 生成可执行的交易计划
  - 提炼双方最强论点
not_for:
  - 替代实际分析（本 skill 只做裁决，不拉数据）
  - 单方面看多/看空
  - 风险辩论（由 risk_team 负责）
---

# Research Manager Skill

在多空辩论结束后，作为"辩论主持人"综合双方最强证据，给出明确裁决
（Buy / Sell / Hold，避免默认 Hold），并输出一份可执行的 investment plan。

## Inputs

- `company_of_interest`（必填）：股票代码
- `market_report` / `sentiment_report` / `news_report` / `fundamentals_report`（必填）：4 份分析师报告
- `investment_debate_state`（必填）：`{history, bull_history, bear_history, current_response, judge_decision, count}`
- `_invest_judge_memory`（可选）：`FinancialSituationMemory`，缺失时用空 memory 兜底

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `investment_plan` | `str` | 裁决 + 理由 + 战略行动（纯文本，无 Markdown header） |
| `investment_debate_state` | `dict` | 更新后的辩论状态（追加 `judge_decision`） |

**注意**：不返回 `messages`。research_manager 的产物是"裁决文本"，不属于对话流。

## Workflow

1. 从 `investment_debate_state.history` 读取完整辩论记录
2. 从 `memory.get_memories(...)` 读取历史相似情境的教训（缺失时跳过）
3. 综合 4 份报告 + 辩论记录 + 历史教训，形成裁决
4. 输出：Recommendation / Rationale / Strategic Actions 三段
5. 保持对话式语气，禁止 Markdown header（`#` / `##`）

## Notes

- **无 tool loop**：单次 `llm.invoke`，无 bind_tools
- **memory 可选**：第 1 期用 `_NullMemory` 兜底；第 2 期把真 memory 通过 `ctx.artifacts["_invest_judge_memory"]` 注入
- **count 不递增**：`investment_debate_state["count"]` 保持原值（辩论已结束）
- **Prompt 长度风险**：`<debate_history>` 无截断，长辩论（4+ 轮）可能几万字符，第 2 期统一处理
