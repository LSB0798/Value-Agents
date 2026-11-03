---
name: risk_team
kind: meta
description: "Runs the 3-way risk debate (Aggressive / Conservative / Neutral) with rolling history compression to keep prompts bounded."
requires:
  - market_report
  - sentiment_report
  - news_report
  - fundamentals_report
  - trader_investment_plan
produces:
  - risk_debate_state
composes:
  - aggressive_debator
  - conservative_debator
  - neutral_debator
capabilities:
  - risk_debate
  - history_compression
  - multi_perspective_risk_assessment
best_for:
  - 风险辩论（多视角）
  - 控制长辩论 prompt 膨胀
not_for:
  - 最终决策（由 portfolio_manager 负责）
  - 研究辩论（由 research_team 负责）
---

# Risk Team Skill

运行 3 方风险辩论（Aggressive / Conservative / Neutral），并**每轮滚动压缩 history**
以控制 prompt 长度。

## Inputs

- `company_of_interest`（必填）
- `market_report` / `sentiment_report` / `news_report` / `fundamentals_report`（必填）
- `trader_investment_plan`（必填）
- `risk_debate_state`（可选，可从上轮继承）
- `_config.max_risk_discuss_rounds`（可选，默认 1）

## Output

| 字段 | 类型 | 说明 |
|---|---|---|
| `risk_debate_state` | `dict` | 含 history / count / latest_speaker / current_*_response / stop_reason |

## Workflow

1. 初始化 `risk_debate_state`（如果 state 里已有则复用）
2. 每轮循环：
   a. **压缩 history**（超过阈值时，保留尾部完整，前部摘要）
   b. Aggressive → Conservative → Neutral 依次发言
   c. 判据：`count >= 3 * max_risk_discuss_rounds` 则停止
3. 返回 `risk_debate_state`（含 `stop_reason`）

## Notes

- **history 滚动压缩**：阈值 30000 chars，超过则保留尾部 15000 chars，前部用 LLM 摘要
- 只压 `history` 字段；`aggressive_history` / `conservative_history` / `neutral_history` 不压
- **无 memory**：3 个 debator 不需要 `FinancialSituationMemory`
- LLM：`ctx.llm`（quick_think，带 callbacks）
