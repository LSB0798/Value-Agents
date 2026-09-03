<p align="center">
  <img src="assets/schema.png" style="width: 80%; height: auto;">
</p>

# TradingAgents with AI Hedge Fund Analysts

**TradingAgents** is a multi‑agent trading decision framework that simulates a hedge fund investment team consisting of **23 AI analysts** — a dedicated news analyst squad (4 analysts) plus **19 master analysts** inspired by legendary investors (e.g., Ben Graham, Warren Buffett, Peter Lynch, Charlie Munger), a bull/bear researcher team, risk analysts, and a portfolio manager. The system generates trading decisions through multi‑round debates and comprehensive signal aggregation.

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
| **Master Analysts** | 19 | Based on the investment philosophies of famous masters (Graham, Buffett, Lynch, Munger, etc.), each performs quantitative analysis and LLM reasoning independently, outputting trading signals (`bullish`/`bearish`/`neutral`) with confidence scores. |

> 💡 **Master Analysts as Skills**: The 19 master analysts have been encapsulated as **Skills** — self‑contained packages consisting of a `SKILL.md` (description, inputs, workflow) and a `skill.py` (execution logic). These Skills can be dynamically loaded and **bound as tools** to the Bull and Bear Researchers, allowing them to call any master analyst on‑demand during the debate to retrieve real‑time valuations, fundamentals, or expert perspectives.

### Workflow

1. **Parallel Analysis**: The News Analysts and the 19 Master Analysts run **in parallel**, each retrieving data and generating reports/signals.
2. **Signal Aggregation**: After all analysts finish, the **SignalAggregator** node collects and prints a consolidated signal summary.
3. **Multi‑Round Debate**: **Bull Researcher** and **Bear Researcher** engage in multi‑round debates based on the aggregated signals and raw reports.  
   - The debate depth is **configurable** (1 round = shallow, 3 rounds = medium, 5 rounds = deep).  
   - During each round, researchers may **call any master analyst Skill** to obtain additional data, challenge the opponent's claims, or reinforce their own thesis — leading to a **spiral of evidence‑based arguments**.
4. **Research Manager Decision**: The **Research Manager** formulates an initial investment plan after the debate.
5. **Trader Execution**: The **Trader** generates specific trade orders.
6. **Risk Debate**: **Aggressive/Conservative/Neutral** risk analysts discuss risk exposure in multiple rounds.
7. **Portfolio Manager**: The **Portfolio Manager** synthesises all information and outputs the final trading decision (`BUY`/`SELL`/`HOLD`/`SHORT` etc.).

### Data Sources

- **Financial Data**: Retrieved via the [Financial Datasets API](https://financialdatasets.ai/) (requires an API key).
- **News Data**: Fetched from multiple providers for cross‑validation and broader coverage:
  - **Alpha Vantage** — global macro and company news.
  - **Finnhub** — real‑time company and market news.
  - **GNews** — worldwide news headlines and articles.
  - **yfinance** — company‑specific and macro news.
- **LLM**: The system uses your locally deployed LLM (e.g., Qwen3‑32B) via an OpenAI‑compatible API endpoint.

### Data Caching

To reduce API calls and speed up repeated analyses, the system **persists data locally** in `dataflows/data_cache/`.  
All data is stored by type and ticker, and new data is merged with existing cached data (deduplicated by date/key), so you won't lose historical data when running new analyses.

The cache directory structure is as follows:

```text
dataflows/data_cache/
├── prices/                           # OHLCV price data (daily)
│   └── daily/
│       ├── AAPL-YFin-daily-2021-07-26-2026-07-26.csv
│       └── MSFT-YFin-daily-2021-07-27-2026-07-27.csv
├── fundamentals/                     # Financial metrics (quarterly/annual)
│   ├── quarterly/
│   │   └── AAPL_roic_quarters.json   # All raw quarterly data
│   └── annual/
│       └── AAPL_edgar_annual.json    # EDGAR annual data
├── line_items/                       # Line items (quarterly/annual)
│   └── AAPL_line_items.json
├── insider/                          # Insider trading records
│   └── AAPL_insider.json
└── news/                             # News articles
    └── AAPL_news.json
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

- SKILL.md: YAML frontmatter (name, description, inputs) plus a detailed workflow description.

- skill.py: A Python module that exports an execute() function.

These Skills are loaded automatically at startup and can be bound as tools to the Bull/Bear Researchers, enabling on‑demand invocation during debates. To add a new master analyst, simply create a new skill folder with the required files, and the system will pick it up without any code changes.

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
FINANCIAL_DATASETS_API_KEY=your-api-key

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
