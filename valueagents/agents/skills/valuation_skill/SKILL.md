---
name: valuation_analyst
description: "Performs comprehensive valuation using DCF, Owner Earnings, EV/EBITDA, and Residual Income models. Aggregates signals with weighted gaps to produce a bullish/bearish/neutral rating with confidence."
best_for:
  - multi-model intrinsic value cross-check
  - mature companies with financial history
  - comprehensive valuation triangulation
not_for:
  - pre-revenue or negative-FCF companies
  - distressed or turnaround situations
  - short-term technical setups
capabilities:
  - dcf_valuation
  - owner_earnings_valuation
  - ev_ebitda_valuation
  - residual_income_valuation
  - weighted_valuation_gap
---

# Valuation Skill

Use this skill when you need a multi-method intrinsic value assessment, incorporating a scenario-based DCF, Buffett-style owner earnings, EV/EBITDA multiple, and residual income approach. This is suitable for mature companies with sufficient financial history.

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
| `reasoning` | Detailed breakdown of each valuation method and the final weighted gap |

```json
{
  "ticker": "AAPL",
  "signal": "bullish",
  "confidence": 72,
  "reasoning": {"dcf_analysis": {...}, "owner_earnings_analysis": {...}, ...}
}
```

## Workflow

1. **Fetch financial metrics (TTM, 8 periods):**
   - Revenue, FCF, net income, debt, interest coverage, ROE, ROIC, etc.

2. **Fetch line items (TTM, 8 periods):**
    - FCF, net income, depreciation, capex, working capital, total debt, cash, interest expense, revenue, operating income, EBIT, EBITDA

3. **Calculate four valuation models:**
    - Owner Earnings: Net Income + Depreciation - Maintenance Capex - ΔWC, discounted at 15%, with 25% margin of safety.
    - Enhanced DCF: Multi-stage FCF DCF with WACC (derived from CAPM + cost of debt), 3 scenarios (bear/base/bull) weighted 20/60/20.
    - EV/EBITDA: Implied equity value using median EV/EBITDA multiple from historical data.
    - Residual Income: Based on book value, net income, and cost of equity (10%), with 20% margin of safety.

4. **Aggregate with weights:**
    - DCF: 35%, Owner Earnings: 35%, EV/EBITDA: 20%, Residual Income: 10%.
    - Compute weighted gap = sum(weight * (value - market_cap) / market_cap) / total_weight

5. **Determine signal:**
    - Bullish if weighted gap > +15%
    - Bearish if weighted gap < -15%
    - Neutral otherwise

6. **Set confidence proportional to absolute gap (capped at 100).**

## Notes
  - This skill provides a comprehensive intrinsic value estimate.
  - It relies heavily on the quality of financial data (TTM).
  - The DCF scenarios account for uncertainty in growth and discount rates.
  - When data is insufficient, it may default to neutral with low confidence.