---
name: market_analyst
kind: core
description: "Technical analysis using price action and up to 8 complementary indicators (SMA/EMA, MACD, RSI, Bollinger, ATR, VWMA). Produces a detailed market report with a Markdown summary table."
requires: []
produces:
  - market_report
capabilities:
  - technical_analysis
  - indicator_selection
  - price_action
  - volume_analysis
best_for:
  - 需要技术面趋势判断
  - 评估支撑阻力、动量、波动率
  - 短线/中线入场时机
not_for:
  - 纯基本面估值
  - 长期持有决策（需 fundamentals 配合）
---

# Market Analyst Skill

对给定 ticker 做技术面分析：先拉 OHLCV，再从指标池中挑选最多 8 个互补指标，
输出一份带 Markdown 汇总表的详细市场报告。

## Inputs

- `ticker`（必填）：股票代码，如 `AAPL`、`0700.HK`
- `end_date`（必填）：分析截止日，`YYYY-MM-DD`
- `api_key`（可选）：Financial Datasets API Key

## Output

写入 Artifact 的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `market_report` | `str` | Markdown 报告（含表格） |
| `messages` | `List[BaseMessage]` | 仅最终 AI 消息（不含 tool 中间态） |

## Workflow

1. 调用 `get_stock_data` 拉取区间 OHLCV
2. 从指标池（SMA/EMA、MACD、RSI、Bollinger、ATR、VWMA）中选 ≤8 个互补指标
3. 每个指标调用一次 `get_indicators`
4. 综合价格行为 + 指标信号，产出带表格的 Markdown 报告
5. 若数据不足，明确写 "insufficient data"，不重试

## Notes

- 工具调用上限：1 次 `get_stock_data` + 8 次 `get_indicators`
- 压缩器：`token_budget=5000`，超阈值触发 4 层压缩
- 语言：由 `config.output_language` 控制
