---
name: aswath_damodaran_analyst
description: "Analyzes a stock using Aswath Damodaran's intrinsic valuation framework: CAPM cost of equity, FCFF DCF, margin of safety, and relative PE. Best for understanding fair value and risk-adjusted returns."
---

# Aswath Damodaran Skill

Use this skill when you need a rigorous, data-driven intrinsic valuation that emphasizes growth, risk, and cash flow. This is particularly useful for assessing whether a stock is undervalued relative to its fundamentals.

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
| `reasoning` | Detailed rationale in Damodaran's analytical style |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 72,
  "reasoning": "Apple's strong revenue growth and high ROIC justify a premium, but the current price offers a 15% margin of safety against my conservative DCF. Risk is moderate with a beta of 1.2 and low debt."
}
```

## Workflow

1. **Fetch financial metrics (TTM, 5 periods):**
   - Revenue, free cash flow, EBIT, interest expense, debt, equity, beta, ROIC

2. **Fetch line items (TTM):**
    - Free cash flow, EBIT, interest expense, capex, depreciation, shares, net income, total debt

3. **Analyze growth and reinvestment:**
    - Revenue CAGR over 5 years (score 0-2)
    - FCFF growth trend (score 0-1)
    - ROIC vs. 10% hurdle (score 0-1)

4. **Analyze risk profile:**
    - Beta (score 0-1 if < 1.3)
    - Debt/Equity (score 0-1 if < 1)
    - Interest coverage (score 0-1 if > 3×)

5. **Calculate intrinsic value using FCFF DCF:**
    - Base FCFF = latest free cash flow
    - Growth = historical revenue CAGR (capped at 18%)
    - 10-year stage 1 with linear fade to terminal growth (4%)
    - Discount rate = CAPM cost of equity (risk-free 4% + β×5%)
    - Terminal value = FCFF_{year10} * (1+g_terminal) / (discount - g_terminal)

6. **Determine margin of safety:**
    - Margin of Safety = (Intrinsic Value - Market Cap) / Market Cap
    - `> 25%`: Bullish
    - `< -25%`: Bearish
    - Otherwise: Neutral

7. **Generate final signal with confidence reflecting:**
    - Quality of growth and reinvestment
    - Risk profile
    - Size of margin of safety
    - Relative PE compared to historical median

## Notes
  - This skill emphasizes fundamental value, not market sentiment.
  - It works best for mature companies with stable cash flows.
  - The DCF uses conservative assumptions and a long-term view.
  - When data is insufficient, it defaults to neutral with low confidence.