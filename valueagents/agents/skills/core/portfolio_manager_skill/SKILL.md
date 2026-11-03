---
name: portfolio_manager
kind: core
description: "Synthesizes the 3-way risk debate (Aggressive / Conservative / Neutral) into a final trading decision with rating (Buy/Overweight/Hold/Underweight/Sell), executive summary, and investment thesis."
requires:
  - market_report
  - sentiment_report
  - news_report
  - fundamentals_report
  - investment_plan
  - trader_investment_plan
  - risk_debate_state
produces:
  - final_trade_decision
  - risk_debate_state
capabilities:
  - risk_debate_synthesis
  - final_rating
  - position_sizing_guidance
  - risk_level_recommendation
best_for:
  - 风险辩论后的最终裁决
  - 输出可执行交易决策（含评级）
  - 综合基本面 + 研究计划 + 交易员计划 + 风险辩论
not_for:
  - 替代实际分析（本 skill 只做裁决，不拉数据）
  - 单一视角判断
  - 风险辩论（由 risk_team 负责）
---

# Portfolio Manager Skill

在风险辩论结束后，作为"投资组合经理"综合研究计划、交易员计划与三方风险辩论，
给出最终交易评级（Buy / Overweight / Hold / Underweight / Sell）+ 执行摘要 + 投资论点。

## Inputs

- `company_of_interest`（必填）：股票代码
- `market_report` / `sentiment_report` / `news_report` / `fundamentals_report`（必填）：4 份分析师报告
- `investment_plan`（必填）：研究经理的裁决
- `trader_investment_plan`（必填）：交易员的执行计划
- `risk_debate_state`（必填）：`{history, aggressive_history, conservative_history, neutral_history, latest_speaker, current_*_response, judge_decision, count}`
- `_portfolio_manager_memory`（可选）：`FinancialSituationMemory`，缺失时用 `_NullMemory` 兜底

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `final_trade_decision` | `str` | 最终决策文本（以 `**Rating**: <xxx>` 开头，含 Exec Summary + Thesis） |
| `risk_debate_state` | `dict` | 更新后的风险辩论状态（追加 `judge_decision`，`latest_speaker="Judge"`） |

**注意**：不返回 `messages`。portfolio_manager 的产物是"决策文本"，不属于对话流。

## Workflow

1. 从 `risk_debate_state.history` 读取完整风险辩论记录
2. 从 `memory.get_memories(...)` 读取历史相似情境的教训（缺失时跳过）
3. 综合 4 份报告 + 研究计划 + 交易员计划 + 风险辩论，形成最终决策
4. 输出三段结构：**Rating** / **Executive Summary** / **Investment Thesis**
5. 响应以 `**Rating**: <one of Buy/Overweight/Hold/Underweight/Sell>` 开头

## Notes

- **无 tool loop**：单次 `llm.invoke`，无 bind_tools
- **memory 可选**：第 1 期用 `_NullMemory` 兜底；第 2 期把真 memory 通过 `ctx.artifacts["_portfolio_manager_memory"]` 注入
- **count 不递增**：`risk_debate_state["count"]` 保持原值（风险辩论已结束）
- **`latest_speaker` 更新为 `"Judge"`**：标记辩论终结
- **Prompt 长度风险**：`<risk_debate_history>` 无截断，mot.txt 里达到 **172678 chars**，第 2 期 risk_team meta skill 化时统一处理滚动压缩
