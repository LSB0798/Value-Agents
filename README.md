<p align="center">
  <img src="assets/schema.png" style="width: 80%; height: auto;">
</p>

# TradingAgents with AI Hedge Fund Analysts

**TradingAgents** is a multi-agent trading decision framework that simulates a hedge fund investment team consisting of:

- **4 News Analysts** — multi-source news intelligence
- **19 Master Analysts** — inspired by legendary investors (Graham, Buffett, Munger, ...)
- **Bull / Bear Researchers** — adversarial debate with dynamic skill invocation
- **Research Manager** — synthesizes debate into an investment plan
- **Trader** — converts the plan into specific orders
- **3 Risk Analysts** (Aggressive / Neutral / Conservative) + **Portfolio Manager** — final decision

The system generates trading decisions through **multi-round debates**, **evidence-based skill selection**, and **comprehensive signal aggregation**.

## 🧠 Core Architecture

### Analyst Team

The system currently includes the following analysts:

| Analyst Type | Count | Description |
|--------------|-------|-------------|
| **News Analysts** | 4 | Multi‑source news intelligence squad. Each analyst fetches from a distinct provider to generate a macro environment report and sentiment signals. |
| &nbsp;&nbsp;├─ Alpha News Analyst | 1 | Retrieves market‑moving news via the **Alpha Vantage** API. |
| &nbsp;&nbsp;├─ Finnhub News Analyst | 1 | Retrieves company‑specific and macro news via the **Finnhub** API. |
| &nbsp;&nbsp;├─ GNews Analyst | 1 | Retrieves broad global news and headlines via the **GNews** API. |
| &nbsp;&nbsp;└─ YFinance News Analyst | 1 | Retrieves company‑specific and global macro news via **yfinance**. |
| **Master Analysts** | 19 | Based on the investment philosophies of famous masters (Graham, Buffett, Lynch, Munger, etc.). Each skill exposes L1 metadata — `best_for` / `not_for` / `capabilities` — that guides on-demand selection by the Bull/Bear Researchers. Each performs quantitative analysis and LLM reasoning independently, outputting trading signals (`bullish`/`bearish`/`neutral`) with confidence scores. |

> 💡 **Master Analysts as Skills**: The 19 master analysts have been encapsulated as **Skills** — 
> self‑contained packages consisting of a `SKILL.md` (metadata + workflow) and a `skill.py` 
> (execution logic). At startup, all skills are loaded into a singleton **SkillRegistry** that 
> provides a lightweight L1 view (name + 120-char description + `best_for` / `not_for` / 
> `capabilities`). During each debate round, Bull and Bear Researchers query this L1 view to 
> select relevant skills, then invoke them on‑demand via the registry — retrieving real‑time 
> valuations, fundamentals, or expert perspectives without loading every skill's full workflow 
> upfront. This is a **progressive disclosure** design: only selected skills have their 
> `## Workflow` injected into their internal LLM prompt.

### Workflow

1. **Parallel Analysis**: The News Analysts and the 19 Master Analysts run **in parallel**, each retrieving data and generating reports/signals.
2. **Signal Aggregation**: After all analysts finish, the **SignalAggregator** node collects and prints a consolidated signal summary.
3. **Multi‑Round Debate**: **Bull Researcher** and **Bear Researcher** engage in multi‑round debates based on the aggregated signals and raw reports.
   - The debate depth is **configurable** (1 round = shallow, 3 rounds = medium, 5 rounds = deep).
   - At each round, each researcher **autonomously selects skills** to fill argument gaps, guided  by the L1 metadata (`best_for` / `not_for` / `capabilities`). Skills already invoked in prior  rounds are excluded from the candidate pool, so evidence accumulates rather than repeats.
   - Selected skills run in **execution stage**: their full `## Workflow` is loaded and injected into the skill's internal LLM prompt, while the researcher only sees the returned signal — a **progressive disclosure** that keeps the debate prompt lightweight.
4. **Research Manager Decision**: The **Research Manager** formulates an initial investment plan after the debate.
5. **Trader Execution**: The **Trader** generates specific trade orders.
6. **Risk Debate**: **Aggressive/Conservative/Neutral** risk analysts discuss risk exposure in multiple rounds.
7. **Portfolio Manager**: The **Portfolio Manager** synthesises all information and outputs the final trading decision (`BUY`/`SELL`/`HOLD`/`SHORT` etc.).

### Data Sources

- **Financial Data**: Retrieved from **yfinance** and **SEC EDGAR** (free, no API key required). The legacy Financial Datasets API is only used as a fallback when both free sources are disabled.
  - **yfinance** — current market data, price history, and quarterly/annual financials.
  - **SEC EDGAR** — authoritative annual filings (10-K) for long-term fundamental analysis.
  - **ROIC API** — quarterly fundamentals for TTM (trailing-twelve-month) calculation.
  - **Finnhub** — insider trades.
  - **Alpha Vantage** — news with built-in sentiment.

### Data Caching

To reduce API calls and speed up repeated analyses, the system **persists data locally** in `dataflows/data_cache/`.  
All data is stored by type and ticker, and new data is merged with existing cached data (deduplicated by date/key), so you won't lose historical data when running new analyses.

The cache directory structure is as follows:

```text
dataflows/data_cache/
├── prices/                           # OHLCV price data (daily)
│   └── daily/
│       └── AAPL-YFin-daily-*.csv
├── fundamentals/                     # Financial metrics (quarterly/annual)
│   ├── quarterly/
│   │   └── AAPL_roic_quarters.json
│   ├── annual/
│   │   └── AAPL_edgar_annual.json
│   └── edgar/                        # Raw SEC EDGAR statements
├── market_cap/                       # 🆕 Per (ticker, date) market cap
│   └── AAPL_2026-06-06.json
├── line_items/
├── insider/
└── news/
```

- **Prices**: CSV files, one per ticker, containing all daily price data (date range as filename).
- **Fundamentals**: JSON files storing quarterly/annual financial metrics and raw statements.
- **Line Items**: JSON files for detailed financial line items (e.g., revenue, debt, cash flow).
- **Insider**: JSON files for insider transaction history.
- **News**: JSON files for company news (from Alpha Vantage, Finnhub, etc.).

> **Note**: The cache is automatically managed. If you ever need to reset it, simply delete the `dataflows/data_cache/` directory or individual files. The system will rebuild them on the next run.

### Optional Feature: RAG (Retrieval‑Augmented Generation)

RAG is disabled by default but can be enabled optionally. When activated, agents can query a local knowledge base (e.g., Buffett’s letters, Munger’s speeches) to enhance their reasoning. For setup details, see the RAG Service Setup section below.

### Skills System (Extension Point)
The master analysts have been refactored into Skills — a modular, plug‑and‑play system. Each skill resides in its own folder under agents/skills/ and consists of:

- SKILL.md: YAML frontmatter with metadata plus a detailed workflow description:
  - `name`, `description` — identity and short summary
  - `best_for` — scenarios where this skill is the right choice
  - `not_for` — anti-patterns to avoid mis-selection
  - `capabilities` — what signals / metrics the skill provides
  - `inputs` — required and optional parameters
  - `## Workflow` — step-by-step execution logic (injected into the skill's internal LLM prompt)

- skill.py: A Python module that exports an execute() function.

These Skills are loaded once at startup via a singleton `SkillRegistry` and exposed to the Bull/Bear Researchers as an on‑demand catalog. During each debate round, a researcher reviews its argument gaps, selects relevant skills by their `best_for` / `not_for` / `capabilities` metadata, and invokes them through the registry to obtain additional analysis.

```text
agents/skills/
├── buffett_skill/
│   ├── SKILL.md
│   └── skill.py
├── munger_skill/
│   ├── SKILL.md
│   └── skill.py
└── ...
```

## 📦 Installation & Usage

### Requirements

- Python 3.13+
- Docker (optional but recommended)

### Clone & Install

```bash
git clone https://github.com/LSB0798/Value-Agents.git
cd Value-Agents
conda create -n valueagents python=3.10
conda activate valueagents
pip install .
```

# Required for financial data
## Data source toggles (recommended: enable both free sources)
USE_YFINANCE=true          # Use yfinance for prices, metrics, quarterly data
USE_EDGAR=true             # Use SEC EDGAR for authoritative annual filings

## Legacy: only needed if you disable both free sources above
FINANCIAL_DATASETS_API_KEY=your-api-key

## News API keys (optional — only required if you use the corresponding analyst)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
FINNHUB_API_KEY=your-finnhub-key
GNEWS_API_KEY=your-gnews-key

## For LLM (OpenAI-compatible local endpoint)
OPENAI_API_BASE=http://your-local-llm:port/v1
OPENAI_API_KEY=dummy

# News API keys (optional — only required if you use the corresponding analyst)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
FINNHUB_API_KEY=your-finnhub-key
GNEWS_API_KEY=your-gnews-key

# For LLM (OpenAI‑compatible local endpoint)
OPENAI_API_BASE=http://your-local-llm:port/v1
OPENAI_API_KEY=dummy

# Run
```
python cli/main.py
```
