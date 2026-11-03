---
name: research_team
kind: meta
description: "Runs the Bull↔Bear research debate with independent used_skills pools, rolling history compression, and a final Research Manager synthesis into investment_plan."
requires:
  - market_report
  - sentiment_report
  - news_report
  - fundamentals_report
produces:
  - investment_debate_state
  - investment_plan
composes:
  - bull_researcher
  - bear_researcher
  - research_manager
capabilities:
  - bull_bear_debate
  - independent_skill_pool
  - debate_history_compression
  - research_synthesis
best_for:
  - 多空辩论并输出 investment_plan
  - Bull/Bear 各自复用 19 个大师 skill 池（互不干扰）
not_for:
  - 最终交易决策（由 portfolio_manager 负责）
  - 风险辩论（由 risk_team 负责）
---

# Research Team Skill

运行 Bull↔Bear 多空辩论，并把最终辩论结果交给 Research Manager 综合成 investment_plan。

## 关键设计

1. **`used_skills` 隔离**：Bull 和 Bear 各自维护独立的 `used_skills` 字典（`used_skills_bull` / `used_skills_bear`）。
   - 实现方式：在调用 `bull_node` / `bear_node` 前，用 `used_skills` key 覆盖 state 里的值，调用后再接住返回值。
   - `bull_researcher.py` / `bear_researcher.py` 内部代码**完全不改**——它们只认 `state["used_skills"]`，谁传就用谁的。
   - 效果：Bull 耗尽 19 个 skill 后，Bear 依然有 19 个可用。

2. **History 滚动压缩**：每轮开头检查 `investment_debate_state["history"]`，超过 30000 字符则保留尾部 15000 字符完整，前部压缩成 400 词摘要。
   - `bull_history` / `bear_history` 不压（`bear_node` 的 step8 需要 `history[-6000:]` 自评）。

3. **停止判据**：搬自 `ConditionalLogic.should_continue_bull/bear`：
   - `should_continue_bull`：Bull 完成后，只有 `current_round > max` 才停，否则必进 Bear。
   - `should_continue_bear`：`completed = current_round - 1`；`completed < min` → 下一轮；`completed >= max` → 停（`max_rounds_reached`）；`no_new_points_streak >= 1` → 停（`argument_space_exhausted`）。

## Inputs

- `company_of_interest`（必填）
- `market_report` / `sentiment_report` / `news_report` / `fundamentals_report`（必填）
- `_config.min_debate_rounds` / `_config.max_debate_rounds`（可选，默认 1/5）
- `_bull_memory` / `_bear_memory` / `_invest_judge_memory`（可选，缺失时 `_NullMemory`）

## Output

| 字段 | 类型 | 说明 |
|---|---|---|
| `investment_debate_state` | `dict` | 含 history / bull_history / bear_history / judge_decision / count / current_round / no_new_points_streak / stop_reason |
| `investment_plan` | `str` | Research Manager 综合的裁决 |

**不返回 messages**：辩论过程通过 `investment_debate_state` 传递，中间 AI 消息不上 graph state（避免污染）。

## Notes

- **Research Manager 的 LLM**：优先用 `ctx.config["_deep_llm"]`（如注入），否则用 `ctx.llm`（通常 quick）。
- **History 压缩阈值**：`_HISTORY_THRESHOLD=30000`，`_KEEP_TAIL_CHARS=15000`，`_SUMMARY_MAX_WORDS=400`。
- **`used_skills` 副作用**：辩论结束后 `state["used_skills"]` 是最后一次 Bear 的池，下游 Trader 不读，无害。
- **max_iter 上限**：`max_rounds + 3`，防御性兜底（正常情况判据会先触发停止）。
