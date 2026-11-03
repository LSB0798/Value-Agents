---
name: cathie_wood_analyst
description: "Analyzes a stock using Cathie Wood's disruptive innovation framework: revenue acceleration, R&D intensity, gross margin expansion, and long-term exponential growth potential. Best for identifying companies leveraging breakthrough technologies with large TAM."
best_for:
  - disruptive innovation themes
  - exponential revenue growth trajectories
  - large TAM breakthrough technologies
not_for:
  - mature stable businesses
  - deep-value or asset plays
  - dividend-focused investments
capabilities:
  - disruptive_potential_score
  - innovation_growth_score
  - high_growth_dcf
  - rd_intensity_analysis
---

# Cathie Wood Skill

Use this skill when you need a forward-looking, growth-oriented analysis focused on disruptive technologies, exponential revenue growth, and long-term market disruption potential. This is especially useful for tech, healthcare, and innovation-driven companies with high growth potential.

## Inputs

- `ticker`: Stock symbol (e.g., AAPL, MSFT, TSLA)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed rationale in Cathie Wood's optimistic, future-focused style |

```json
{
  "ticker": "TSLA",
  "signal": "bullish",
  "confidence": 82,
  "reasoning": "Tesla is at the forefront of the autonomous driving and energy revolution. Revenue growth is accelerating at 45% YoY, with gross margins expanding to 25% and R&D intensity at 18% of revenue. The company is reinvesting heavily in innovation, positioning itself to capture a significant share of the $10T transportation and energy markets. Despite short-term volatility, the long-term exponential growth trajectory remains intact."
}
```

## Workflow

1. **Fetch financial metrics (annual, 5 periods):**
   - Revenue, gross margin, operating margin, debt-to-equity, free cash flow, total assets, total liabilities, dividends, outstanding shares, R&D, capex, operating expense

2. **Analyze disruptive potential (score normalized to 0-5):**
    - Revenue growth acceleration (score 0-3)
    - Gross margin expansion (score 0-2)
    - Operating leverage (revenue growing faster than expenses) (score 0-2)
    - R&D intensity (score 0-3)

3. **Analyze innovation-driven growth (score normalized to 0-5):**
    - R&D investment growth and intensity trend (score 0-5)
    - FCF consistency and growth (score 0-3)
    - Operating margin strength and trend (score 0-3)
    - CAPEX intensity and growth (score 0-2)
    - Growth reinvestment vs dividends (score 0-2)

4. **Perform valuation (score 0-3):**
    - High-growth DCF (20% growth, 15% discount, 25x terminal multiple)
    - Margin of safety > 50% (score 0-3), > 20% (score 0-1)

5. **Aggregate scores:**
    - Disruptive + Innovation + Valuation = total_score (max 15)
    - Bullish if >= 70% of max, Bearish if <= 30%, Neutral otherwise

6. **Generate final signal with confidence reflecting the strength of the disruptive thesis.**

## Notes
  - This skill emphasizes long-term disruptive potential over short-term profitability.
  - It is most suitable for companies in high-growth sectors (AI, robotics, genomics, fintech, blockchain).
  - The valuation assumes high growth and a long time horizon, which may not be appropriate for mature, slow-growth companies.
  - When data is insufficient, it defaults to neutral with low confidence.