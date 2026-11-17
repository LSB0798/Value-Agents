# Regression Baseline Library

Phase 0 基线库。3 个 case，每个跑 3 次取范围（LLM 随机性）。

## Case 列表

| Case | Ticker | Date | Expected Rating | 用途 |
|---|---|---|---|---|
| B1 | NFLX | 2026-09-03 | UNDERWEIGHT | 主 case，完整 pipeline |
| B2 | GOOGL | 2026-09-10 | OVERWEIGHT | Chat 主 case |
| B3 | MSFT | 2026-01-16 | HOLD | 中位 case，验证 hold |

## Baseline JSON 格式

```json
{
  "case_id": "B1",
  "ticker": "NFLX",
  "end_date": "2026-09-03",
  "captured_at": "...",
  "source": "v1.0_docs | phase0_capture",
  "config": {"research_depth": 5, "llm": "qwen3.6-27B", "temperature": 0.3},
  "expected": {
    "final_rating": "UNDERWEIGHT",
    "report_lengths": {"market_report": [lo, hi], ...},
    "tokens_in_range": [lo, hi],
    "tokens_out_range": [lo, hi],
    "llm_calls_range": [lo, hi],
    "elapsed_minutes_range": [lo, hi],
    "master_signals_summary": {"bullish": n, "bearish": n, "neutral": n}
  }
}
