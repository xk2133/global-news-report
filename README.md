# Global News Report

Daily automated "Global Top News" HTML report — market data via Wind MCP, news via web search.

## Features

- **15 Market Indicators**: Dow, S&P 500, Nasdaq, Gold, WTI, DXY, USD/CNY, US 10Y + Mag 7 stocks
- **YTD Sparklines**: SVG trend lines for all indicators
- **Bilingual News Cards**: English headlines with Chinese summaries, 4 tabbed sections
- **Self-Contained HTML**: Single file, no external dependencies, mobile-responsive
- **Wind MCP Powered**: Three-track architecture (quote / price indicators / economic data)

## Report Structure

| Tab | Content |
|-----|---------|
| Financial | 8 indicators table + 3-5 market news |
| Technology | Mag 7 stocks table + 3-5 tech news |
| Political | 3-5 geopolitics stories (T1 sources only) |
| Highlights | World, sports, crypto, defense |

## Data Sources

- **Market Data**: [Wind MCP](https://github.com/Wind-Information-Co-Ltd/wind-skills) (15/15 indicators)
  - Track A: DJI, SPX, IXIC, USD/CNY via `index_data.get_index_quote`
  - Track B: AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA via `stock_data.get_stock_price_indicators`
  - Track C: Gold, WTI, DXY, US 10Y via `economic_data.get_economic_data`
- **News**: WebSearch + WebFetch (AP, Reuters, Bloomberg, WSJ, CNBC, etc.)

## Usage

```
@skill:global-news-report
```

Run manually or schedule as a daily automation (recommended: 08:30 CST, weekdays).

## Output

`Global News Report-YYYYMMDD.html` — ready to view in any browser.

## Dependencies

- [Wind MCP Skill](https://github.com/Wind-Information-Co-Ltd/wind-skills) — for market data
- WebSearch — for news collection
- No API keys, no Python scripts, no Finnhub/NewsAPI

## Version

v2.3.0 — Wind MCP three-track architecture, self-contained HTML template, bilingual cards
