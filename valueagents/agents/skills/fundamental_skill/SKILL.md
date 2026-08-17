---
name: fundamental_analyst
description: "Provides a systematic, multi-dimensional fundamental analysis of a stock: profitability, growth, financial health, and valuation. Uses quantitative thresholds (ROE >15%, margin >20%, revenue growth >10%, etc.) to generate a signal with supporting evidence."
---

# Fundamental Analyst Skill

Use this skill when you need a comprehensive, data-driven assessment of a company's fundamentals across four key dimensions: profitability, growth, financial health, and valuation. This is a universal analysis suitable for any stock.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, KO)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 (based on signal consistency) |
| `reasoning` | Detailed breakdown of each dimension with specific metrics |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 50.0,
  "reasoning": {
    "profitability_signal": {
      "signal": "bullish",
      "details": "ROE: 151.91%, Net Margin: 26.77%, Op Margin: 34.61%"
    },
    "growth_signal": {
      "signal": "neutral",
      "details": "Revenue Growth: 6.45%, Earnings Growth: 9.87%"
    },
    "financial_health_signal": {
      "signal": "neutral",
      "details": "Current Ratio: 0.89, D/E: 2.04"
    },
    "price_ratios_signal": {
      "signal": "bearish",
      "details": "P/E: 29.80, P/B: 34.30, P/S: 8.09"
    }
  }
}
```

## Workflow

1. **Fetch financial metrics (TTM, 10 periods):**
   - ROE, net margin, operating margin
   - Revenue growth, earnings growth, book value growth
   - Current ratio, debt-to-equity, FCF per share, EPS
   - P/E, P/B, P/S ratios

2. **Analyze profitability (score 0-3):**
    - ROE > 15% (score +1)
    - Net margin > 20% (score +1)
    - Operating margin > 15% (score +1)
    - Bullish if >= 2, Bearish if 0, Neutral otherwise

3. **Analyze growth (score 0-3):**
    - Revenue growth > 10% (score +1)
    - Earnings growth > 10% (score +1)
    - Book value growth > 10% (score +1)
    - Bullish if >= 2, Bearish if 0, Neutral otherwise

4. **Analyze financial health (score 0-3):**
    - Current ratio > 1.5 (score +1)
    - Debt-to-equity < 0.5 (score +1)
    - FCF > EPS * 0.8 (score +1)
    - Bullish if >= 2, Bearish if 0, Neutral otherwise

5. **Analyze valuation ratios (score 0-3):**
    - P/E < 25 (score +1) — note: lower is better
    - P/B < 3 (score +1)
    - P/S < 5 (score +1)
    - Bearish if >= 2, Bullish if 0, Neutral otherwise

6. **Aggregate signals:**
    - Compare bullish vs bearish signals
    - Confidence = (dominant signals / total signals) * 100

7. **Generate final signal with detailed reasoning for each dimension.**

## Notes
  - This is a systematic, rule-based analysis with quantitative thresholds.
  - It does not incorporate qualitative factors (moats, management, industry trends).
  - The analysis uses TTM data for the most current picture.
  - Confidence reflects signal consistency across dimensions.
  - When data is insufficient, defaults to neutral with low confidence.
