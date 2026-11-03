---
name: rakesh_jhunjhunwala_analyst
description: "Analyzes a stock using Rakesh Jhunjhunwala's value-investing framework: quality growth, high ROE, low debt, strong cash flow, and margin of safety. Best for identifying compounding machines with sustainable competitive advantages."
best_for:
  - quality-growth businesses with high ROE
  - long-term compounding opportunities
  - shareholder-friendly management
not_for:
  - speculative or unprofitable companies
  - deep cyclicals or turnarounds
  - short-term momentum trades
capabilities:
  - profitability_and_roe_analysis
  - growth_cagr_analysis
  - balance_sheet_review
  - margin_of_safety_dcf
---

# Rakesh Jhunjhunwala Skill

Use this skill when you need a growth-oriented value analysis focused on high-quality businesses with strong ROE, clean balance sheets, consistent earnings growth, and shareholder-friendly management. This is especially useful for identifying long-term compounding opportunities in emerging or established markets.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, TITAN)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed rationale in Jhunjhunwala's pragmatic, conviction-driven style |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 65,
  "reasoning": "Apple demonstrates exceptional ROE of 151% and strong earnings growth, with a clean balance sheet and consistent free cash flow. However, the current valuation offers no margin of safety, trading at a premium to intrinsic value. A better entry point is needed to justify conviction."
}
```

## Workflow

1. **Fetch financial metrics (TTM, 5 periods):**
   - ROE, operating margin, net income, EPS, EBIT

2. **Fetch line items (annual, up to 5 periods):**
    - Net income, EPS, EBIT, operating income, revenue, operating margin
    - Total assets, total liabilities, current assets, current liabilities
    - Free cash flow, dividends, share issuance/buybacks

3. **Analyze profitability (score 0-8):**
    - ROE > 20% (score 0-3), > 15% (score 0-2), > 10% (score 0-1)
    - Operating margin > 20% (score 0-2), > 15% (score 0-1)
    - EPS CAGR > 20% (score 0-3), > 15% (score 0-2), > 10% (score 0-1)

4. **Analyze growth (score 0-7):**
    - Revenue CAGR > 20% (score 0-3), > 15% (score 0-2), > 10% (score 0-1)
    - Net income CAGR > 25% (score 0-3), > 20% (score 0-2), > 15% (score 0-1)
    - Growth consistency > 80% years positive (score 0-1)

5. **Analyze balance sheet (score 0-4):**
    - Debt-to-assets < 0.5 (score 0-2), < 0.7 (score 0-1)
    - Current ratio > 2.0 (score 0-2), > 1.5 (score 0-1)

6. **Analyze cash flow (score 0-3):**
    - Positive FCF (score 0-2)
    - Dividend payments (score 0-1)

7. **Analyze management actions (score 0-2):**
    - Share buybacks (score 0-2)
    - No dilution (score 0-1)

8. **Calculate intrinsic value:**
    - Simple DCF with conservative growth and quality-adjusted discount rate (12-18%)
    - Margin of Safety = (Intrinsic Value - Market Cap) / Market Cap

9. **Decision rules:**
    - Margin of Safety > 30% → Bullish
    - Margin of Safety < -30% → Bearish
    - Otherwise: Use quality score as tie-breaker
        - Quality ≥ 0.7 AND total_score ≥ 60% max → Bullish
        - Quality ≤ 0.4 OR total_score ≤ 30% max → Bearish
        - Otherwise → Neutral

10. **Confidence based on margin of safety and quality score.**

## Notes
  - This skill emphasizes "buying quality at a fair price" rather than "buying cheap at any price."
  - It is most suitable for companies with consistent earnings growth and strong ROE.
  - Jhunjhunwala was known for concentrated, high-conviction positions with a long-term view.
  - When data is insufficient, it defaults to neutral with low confidence.