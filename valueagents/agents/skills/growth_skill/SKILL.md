---
name: growth_analyst
description: "Analyzes a stock from a growth investor's perspective: revenue/EPS/FCF growth trends, PEG ratio, margin expansion, insider conviction, and financial health. Best for identifying companies with sustainable growth momentum."
best_for:
  - revenue and EPS growth trajectory
  - GARP valuation via PEG ratio
  - companies in expansion phase
not_for:
  - deep value or asset plays
  - mature slow-growth businesses
  - distressed companies
capabilities:
  - growth_trend_analysis
  - peg_valuation
  - margin_expansion_tracking
  - insider_conviction
---

# Growth Analyst Skill

Use this skill when you need to evaluate a stock's growth trajectory, valuation relative to growth (PEG), and the sustainability of its growth through margin trends and insider conviction. This is especially useful for companies in expansion phases.

## Inputs
- `ticker`: Stock symbol (e.g., AAPL, NVDA, TSLA)
- `end_date`: Analysis end date in YYYY-MM-DD format
- `api_key`: (Optional) Financial datasets API key. If not provided, the system will attempt to use environment variables.

## Output

Returns a JSON object with the following structure:

| Field | Description |
|-------|-------------|
| `signal` | One of "bullish", "bearish", or "neutral" |
| `confidence` | Confidence score from 0 to 100 |
| `reasoning` | Detailed breakdown including growth trends, valuation, margins, insider conviction, and financial health |

```json
{
  "ticker": "NVDA",
  "signal": "bullish",
  "confidence": 85,
  "reasoning": {
    "historical_growth": { "score": 0.85, "revenue_growth": 0.45, "eps_growth": 0.52, "fcf_growth": 0.38 },
    "growth_valuation": { "score": 0.75, "peg_ratio": 0.85, "price_to_sales_ratio": 12.5 },
    "margin_expansion": { "score": 0.70, "gross_margin": 0.65, "operating_margin": 0.35 },
    "insider_conviction": { "score": 0.80, "net_flow_ratio": 0.25 },
    "financial_health": { "score": 0.90, "debt_to_equity": 0.3, "current_ratio": 2.1 },
    "final_analysis": { "signal": "bullish", "confidence": 85, "weighted_score": 0.72 }
  }
}
```

## Workflow

1. **Fetch financial metrics (TTM, 12 periods):**
    - Revenue growth, EPS growth, FCF growth
    - PEG ratio, price-to-sales ratio
    - Gross margin, operating margin, net margin (and their trends)
    - Debt-to-equity, current ratio

2. **Fetch insider trades (1000 records):**
    - Calculate net buying/selling ratio

3. **Analyze historical growth (weight 40%, score 0-1):**
    - Recent revenue growth > 20% (score +0.4), > 10% (score +0.2)
    - Accelerating revenue trend (score +0.1)
    - Recent EPS growth > 20% (score +0.25), > 10% (score +0.1)
    - Accelerating EPS trend (score +0.05)
    - FCF growth > 15% (score +0.1)

4. **Analyze growth valuation (weight 25%, score 0-1):**
    - PEG < 1.0 (score +0.5), < 2.0 (score +0.25)
    - P/S < 2.0 (score +0.5), < 5.0 (score +0.25)

5. **Analyze margin expansion (weight 15%, score 0-1):*
    - Gross margin > 50% (score +0.2), expanding trend (score +0.2)
    - Operating margin > 15% (score +0.2), expanding trend (score +0.2)
    - Net margin trend expanding (score +0.2)

6. **Analyze insider conviction (weight 10%, score 0-1):**
    - Net flow ratio > 0.5 (score 1.0), > 0.1 (score 0.7)
    - Neutral ratio (score 0.5), negative (score 0.2)

7. **Check financial health (weight 10%, score 0-1):**
    - Start at 1.0, deduct for high debt and low current ratio

8. **Aggregate scores with weights:**
    - Weighted_score = 0.4growth + 0.25valuation + 0.15margins + 0.1insider + 0.1*health
    - Bullish if > 0.6, Bearish if < 0.4, Neutral otherwise

9. **Generate final signal with confidence based on distance from neutral.**

## Notes
  - This skill focuses on growth momentum and sustainability.
  - It is most suitable for companies with strong revenue and earnings growth.
  - Valuation is assessed via PEG and P/S, which are growth-oriented metrics.
  - Insider conviction provides a qualitative signal on management confidence.
  - When data is insufficient, defaults to neutral with low confidence.