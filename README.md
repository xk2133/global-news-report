# Global News Report

Daily automated "Global Top News" HTML report — market data via Wind MCP, news via web search.

## Features

- **15 Market Indicators**: Dow, S&P 500, Nasdaq, Gold, WTI, DXY, USD/CNH (Offshore), US 10Y + Mag 7 stocks
- **YTD Sparklines**: SVG trend lines for all 15 indicators
- **Bilingual News Cards**: English headlines with Chinese summaries, 4 tabbed sections
- **Self-Contained HTML**: Single file, no external dependencies, mobile-responsive
- **Wind MCP Powered**: Three-track architecture (index_kline / price_indicators / economic_data)
- **Source Tier Filtering**: T1/T2/T3 grading ensures high-quality English sources only

## Report Structure

| Tab | Content |
|-----|---------|
| Financial | 8 indicators table + 3-5 market news (T1+T2 sources, ≥2 T1) |
| Technology | Mag 7 stocks table + 3-5 tech news (T1/T2/T3 sources) |
| Political | 3-5 geopolitics stories (T1 sources only) |
| Highlights | World, sports, crypto, defense (T1/T2/T3 sources) |

## Data Sources

- **Market Data**: [Wind MCP](https://github.com/Wind-Information-Co-Ltd/wind-skills) (15/15 indicators)
  - Track A: DJI, SPX, IXIC, USD/CNH via `index_data.get_index_kline`
  - Track B: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA via `stock_data.get_global_stock_price_indicators` (7 serial calls, no comma-separated windcodes)
  - Track C: Gold, WTI, DXY, US 10Y via `economic_data.get_economic_data` (single call, filter by code)
- **News**: WebSearch + WebFetch (Reuters, AP, Bloomberg, WSJ, CNBC, etc.)
- **Fallback**: If Wind MCP unavailable, generates news-only report (Step 2 + Step 3)

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
- No API keys, no Python scripts

> **Windows users**: Wind MCP CLI calls must be done serially (not parallel with `&`); Python `subprocess.run()` may return empty stdout — redirect CLI output to temp files as a workaround.

## Version

v2.5.1 — USDCNH migrated to economic_data (G0002329); Windows subprocess notes added; three-track architecture with correct tool names.
