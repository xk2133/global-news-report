# Global News Report

Daily automated "Global Top News" HTML report — market data via Wind MCP, news via web search.

## Features

- **15 Market Indicators**: Dow, S&P 500, Nasdaq, US 10Y, DXY, USD/CNH, Gold, WTI + Mag 7 stocks (股→债→汇→商 order)
- **YTD Sparklines**: SVG trend lines for all 15 indicators
- **Bilingual News Cards**: English headlines with Chinese summaries, 4 tabbed sections
- **Self-Contained HTML**: Single file, no external dependencies, mobile-responsive
- **Wind MCP Powered**: Three-track architecture (index_kline / price_indicators / economic_data)
- **Source Tier Filtering**: T1/T2/T3 grading ensures high-quality English sources only
- **Scripted Pipeline**: Market data fetch, compute, and HTML generation fully scripted (no LLM HTML writing)

## Architecture

```
SKILL.md                   ← Workflow orchestration (call scripts, don't write HTML)
references/
├── news-filtering.md      ← Source tiers, section rules, BANNED list
└── windows-exec-rules.md  ← Windows-specific execution rules
assets/
└── report-template.html   ← HTML/CSS template with {PLACEHOLDERS}
scripts/
├── generate_fetch.py      ← Generates Bash script for Wind MCP data fetching (19 serial calls)
├── compute_market.py      ← Raw Wind JSON → standardized market_data.json (validates EDB codes, computes YTD)
└── generate_html.py       ← market_data.json + news_data.json → final HTML (sparklines, tables, news cards)
```

## Report Structure

| Tab | Content |
|-----|---------|
| Financial | 8 indicators table + 3-5 market news (T1+T2 sources, ≥2 T1) |
| Technology | Mag 7 stocks table + 3-5 tech news (T1/T2/T3 sources) |
| Political | 3-5 geopolitics stories (T1 sources only) |
| Highlights | World, sports, crypto, defense (T1/T2/T3 sources) |

## Data Sources

- **Market Data**: [Wind MCP](https://github.com/Wind-Information-Co-Ltd/wind-skills) (15/15 indicators)
  - Track A: DJI, SPX, IXIC via `index_data.get_index_kline`
  - Track B: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA via `stock_data.get_global_stock_price_indicators` + `get_global_stock_kline` (7+7 serial calls, no comma-separated windcodes)
  - Track C: Gold, WTI, DXY, US 10Y, USD/CNH via `economic_data.get_economic_data` (5 EDB codes, single call)
- **News**: WebSearch + WebFetch (Reuters, AP, Bloomberg, WSJ, CNBC, etc.)
- **Fallback**: If Wind MCP probe fails, fetch market data from MarketWatch (Step 1d)

## Usage

```
@skill:global-news-report
```

Run manually or schedule as a daily automation (recommended: 08:30 CST, weekdays).

## Output

`Global News Report-YYYYMMDD.html` — ready to view in any browser.

## Dependencies

- [Wind MCP Skill](https://github.com/Wind-Information-Co-Ltd/wind-skills) — for market data (Wind terminal must be running)
- WebSearch / WebFetch — for news collection
- Python 3.11+ — for scripts (generate_fetch.py, compute_market.py, generate_html.py)

## Version

v3.2.0 — HTML generation scripted (generate_html.py); SKILL.md精简 to 110 lines; references/news-filtering.md 只保留过滤规则; 市场数据表顺序改为股债汇商。
