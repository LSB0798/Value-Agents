---
name: ben_graham_analyst
description: "Analyzes a stock using Benjamin Graham's value investing principles: earnings stability, financial strength, net-net value, Graham Number, and margin of safety. Best for deep-value, conservative investment opportunities."
---

# Benjamin Graham Skill

Use this skill when you need a classic value-oriented analysis focused on downside protection, balance sheet strength, and a significant margin of safety. This is especially useful for identifying undervalued stocks with solid fundamentals.

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
| `reasoning` | Detailed rationale in Graham's conservative style |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 45,
  "reasoning": "Earnings are stable and financial strength is solid, but the stock is overvalued relative to the Graham Number and net-net value, offering no margin of safety."
}
```

## Workflow

1. **Fetch financial metrics (annual, 10 periods):**
   - Earnings per share, revenue, net income, book value per share, total assets, total liabilities, current assets, current liabilities, dividends, outstanding shares

2. **Analyze earnings stability:**
    - Check if EPS is positive in most periods (score 0-3)
    - Check if EPS grew from earliest to latest (score 0-1)

3. **Analyze financial strength:**
    - Current ratio >= 2.0 (score 0-2), >= 1.5 (score 0-1)
    - Debt ratio (total liabilities / total assets) < 0.5 (score 0-2), < 0.8 (score 0-1)
    - Dividend track record (score 0-1 if consistent)

4. **Perform Graham valuation:**
    - Net-Net Check: (Current Assets - Total Liabilities) vs. Market Cap (score 0-4 if NCAV > Market Cap, 0-2 if partial discount)
    - Graham Number: sqrt(22.5 * EPS * Book Value per Share)
    - Margin of Safety = (Graham Number - Price) / Price (score 0-3 if >50%, 0-1 if >20%)

5. **Aggregate scores:**
    - Max possible score = 15
    - Bullish if >= 70% of max, Bearish if <= 30%, Neutral otherwise

6. **Generate final signal with confidence reflecting the strength of the value case.**

## Notes
  - This skill emphasizes safety and margin of safety above all else.
  - It is most suitable for mature, dividend-paying companies with low debt.
  - Graham would avoid speculative businesses with volatile earnings.
  - The skill relies on annual data; TTM data may be less reliable for Graham's long-term perspective.
  - When data is insufficient, it defaults to neutral with low confidence.