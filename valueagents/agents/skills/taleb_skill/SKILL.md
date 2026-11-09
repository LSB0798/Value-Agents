---
name: nassim_taleb_analyst
description: "Analyzes a stock using Nassim Taleb's antifragility framework: tail risk, convexity, fragility, skin in the game, volatility regime, and black swan signals. Best for assessing robustness to rare events and disorder."
best_for:
  - tail-risk and fragility assessment
  - antifragility and convexity analysis
  - robustness to rare extreme events
not_for:
  - plain vanilla intrinsic valuation
  - smooth-return compounders
  - short-term momentum trades
capabilities:
  - tail_risk_analysis
  - antifragility_score
  - convexity_payoff_check
  - volatility_regime_analysis
  - black_swan_sentinel
---

# Nassim Taleb Skill

Use this skill when you need to evaluate a stock's resilience to extreme events, asymmetric payoff potential, and vulnerability to tail risks. This is especially useful for understanding whether a company benefits from volatility and disorder (antifragile) or is fragile to shocks.

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
| `reasoning` | Detailed rationale in Taleb's vocabulary (antifragile, convexity, skin in the game, etc.) |

```json
{
  "ticker": "AAPL",
  "signal": "neutral",
  "confidence": 50,
  "reasoning": "Moderate tail risk with fat tails; net cash positive but high leverage; mixed convexity signals; insider selling; low vol regime raises turkey problem concerns."
}
```

## Workflow

1. **Fetch price data (1 year):**
   - Daily OHLCV for tail risk, volatility, and drawdown analysis

2. **Fetch financial metrics (TTM, 10 periods):**
    - Operating margin, net margin, debt-to-equity, earnings growth, interest coverage

3. **Fetch line items (TTM, 5 periods):**
    - FCF, net income, total debt, cash, assets, liabilities, revenue, operating income, R&D, capex, shares

4. **Fetch insider trades (1 year):**
    - Skin in the game (net insider buying)

5. **Fetch company news (100 articles, 1 year):**
    - Black swan sentinel (negative sentiment, volume spikes)

6. **Fetch market cap**

7. **Analyze tail risk (max 8):**
    - Kurtosis (fat tails) (score 0-2)
    - Skewness (positive skew favors convexity) (score 0-2)
    - Tail ratio (upside/downside asymmetry) (score 0-2)
    - Max drawdown (score 0-2)

8. **Analyze antifragility (max 10):**
    - Net cash position (score 0-3)
    - Debt-to-equity (score 0-2)
    - Operating margin stability (score 0-3)
    - FCF consistency (score 0-2)

9. **Analyze convexity (max 10):**
    - R&D optionality (score 0-3)
    - Upside/downside ratio (score 0-2)
    - Cash optionality (score 0-3)
    - FCF yield (score 0-2)

10. **Analyze fragility (via negativa, max 8):**
    - Debt-to-equity (score 0-3)
    - Interest coverage (score 0-2)
    - Earnings volatility (score 0-2)
    - Net margin buffer (score 0-1)

11. **Analyze skin in the game (max 4):**
    - Net insider buying ratio (score 0-4)

12. **Analyze volatility regime (max 6):**
    - Current vs historical volatility (low vol = danger) (score 0-4)
    - Vol-of-vol (stability of volatility) (score 0-2)

13. **Analyze black swan sentinel (max 4):**
    - Negative news + volume spikes (score 0-3)
    - Contrarian opportunity (score +1)

14. **Aggregate scores:**
    - Total max = 50 (8+10+10+8+4+6+4)
    - Bullish if score >= 35 (70%), Bearish if <= 15 (30%), Neutral otherwise

15. **Generate final signal with Taleb's vocabulary and a short justification (<150 chars).**

## Notes
  - This skill emphasizes robustness to rare events and disorder.
  - It is most suitable for assessing tail risk and antifragility.
  - Taleb would avoid fragile businesses (high debt, volatile earnings, thin margins).
  - Low volatility regimes are dangerous ("turkey problem").
  - Skin in the game (insider buying) is a positive signal.
  - When data is insufficient, defaults to neutral with low confidence.