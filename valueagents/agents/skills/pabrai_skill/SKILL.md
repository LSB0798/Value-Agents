---
name: mohnish_pabrai_analyst
description: "Analyzes a stock using Mohnish Pabrai's 'Heads I win, tails I don't lose much' framework: downside protection, FCF yield, asset-light business model, and 2-3 year doubling potential. Best for identifying low-risk, high-uncertainty value opportunities."
---

# Mohnish Pabrai Skill

Use this skill when you need a value-oriented analysis focused on capital preservation first, with asymmetric upside. Pabrai's approach emphasizes simple businesses, high FCF yields, low leverage, and the potential to double capital in 2-3 years with minimal downside.

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
| `reasoning` | Detailed rationale in Pabrai's candid, checklist-driven style |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 45.0,
  "reasoning": "Moderate downside protection with net cash position. FCF yield of 3.4% is below Pabrai's threshold of 5-10%. Limited doubling potential given current valuation and growth trajectory."
}
```

## Workflow

1. **Fetch financial metrics (annual, 8 periods):**
   - Revenue, gross profit, gross margin, operating income, operating margin, net income, FCF

2. **Fetch line items (annual, 8 periods):**
    - Total debt, cash, current assets, current liabilities, shareholders equity
    - Capex, depreciation, outstanding shares

3. **Fetch market cap**

4. **Analyze downside protection (weight 45%):**
    - Net cash position (score +3 if cash > debt)
    - Current ratio >= 2.0 (score +2), >= 1.2 (score +1)
    - D/E < 0.3 (score +2), < 0.7 (score +1)
    - Positive and improving FCF (score +2), positive but declining (score +1)

5. **Analyze cash yield & valuation (weight 35%):**
    - FCF yield > 10% (score +4), > 7% (score +3), > 5% (score +2), > 3% (score +1)
    - Asset-light business: capex/revenue < 5% (score +2), < 10% (score +1)

6. **Analyze doubling potential (weight 20%):**
    - Revenue growth > 15% (score +2), > 5% (score +1)
    - FCF growth > 20% (score +3), > 8% (score +2), > 0% (score +1)
    - High FCF yield > 8% can drive doubling via compounding (score +3)

7. **Aggregate scores:**
    - Weighted score = 0.45downside + 0.35valuation + 0.20*double
    - Bullish if >= 7.5, Bearish if <= 4.0, Neutral otherwise

8. **Generate final signal with Pabrai's candid, checklist-driven reasoning.**

## Notes
  - This skill prioritizes downside protection above all else.
  - Pabrai's mantra: "Heads I win, tails I don't lose much."
  - It favors simple, understandable businesses with durable moats.
  - The analysis uses annual data for long-term trend assessment.
  - When data is insufficient, defaults to neutral with low confidence.