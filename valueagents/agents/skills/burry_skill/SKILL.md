---
name: michael_burry_analyst
description: "Analyzes a stock using Michael Burry's deep-value, contrarian framework: FCF yield, EV/EBIT, balance sheet strength, insider activity, and contrarian sentiment. Best for identifying undervalued opportunities with catalysts."
---

# Michael Burry Skill

Use this skill when you need a deep-value, contrarian analysis focused on hard numbers, downside protection, and catalysts like insider buying or negative sentiment. This is especially useful for identifying stocks that the market may be mispricing.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, KO)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed rationale in Burry's terse, data-driven style |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 45.0,
  "reasoning": "FCF yield 3.2%. EV/EBIT 15.4. Debt-to-equity 1.2. Mixed signals: reasonable valuation but no significant margin of safety."
}
```

## Workflow

1. **Fetch financial metrics (TTM, 5 periods):**
   - EV/EBIT, debt-to-equity, FCF yield, etc.

2. **Fetch line items:**
    - Free cash flow, net income, total debt, cash, total assets, total liabilities, outstanding shares, share issuance/buybacks

3. **Fetch insider trades (last 12 months):**
    - Net insider buying/selling activity

4. **Fetch company news (250 articles, last 12 months):**
    - Negative sentiment count for contrarian signals

5. **Fetch market cap**

6. **Analyze value (max score 6):**
    - FCF yield >= 15% (score +4), >= 12% (score +3), >= 8% (score +2)
    - EV/EBIT < 6 (score +2), < 10 (score +1)

7. **Analyze balance sheet (max score 3):**
    - Debt-to-equity < 0.5 (score +2), < 1.0 (score +1)
    - Net cash position (cash > debt) (score +1)

8. **Analyze insider activity (max score 2):**
    - Net insider buying (score +2 if buy/sell ratio > 1x, else +1)
    - Net insider selling (score 0)

9. **Analyze contrarian sentiment (max score 1):**
    - 5+ negative headlines (score +1) — "the more hated, the better"

10. **Aggregate scores:**
    - Max possible = 12 (6+3+2+1)
    - Bullish if >= 70% of max, Bearish if <= 30%, Neutral otherwise

11. **Generate final signal with Burry's terse, data-driven voice.**

## Notes
  - This skill emphasizes hard numbers over qualitative narratives.
  - It looks for catalysts: insider buying, buybacks, or asset sales.
  - Contrarian sentiment: negative press can be a positive signal.
  - The analysis uses TTM data and 12-month lookback for insider/news.
  - When data is insufficient, defaults to neutral with low confidence.