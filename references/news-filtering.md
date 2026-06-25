# News Filtering Rules

## Source Tiers

| Tier | Sources | Rule |
|------|---------|------|
| **T1** | Reuters, AP, Bloomberg, BBC, **WSJ** | Political section T1-only |
| **T2** | CNBC, **CNN**, NYT, FT, MarketWatch, Barron's, The Information | Financial section T1+T2 only |
| **T3** | TechCrunch, Wired, The Verge, Ars Technica, VentureBeat | Tech section only |
| **BANNED** | CoinStats, TechStartups, CoinTelegraph, ValueWalk, Business Insider tech, Seeking Alpha, Fortune, Forbes | Zero tolerance, any section |

## Section-Level Rules

| Section | Allowed Tiers | T1 Minimum |
|---------|--------------|------------|
| Financial | **T1, T2 only** | ≥ 2 stories must be T1 |
| Technology | **T1, T2, T3** | — |
| Political | **T1 only** | All stories must be T1 |
| Other | T1, T2, T3 | — |

## General Rules

- All sources English-only. NO sina, qq, 36kr, eastmoney, or any Chinese-language sources.
- Same event → merge into primary section, cite highest-tier source.
- Recency hard limit: < 24 hours.
- Each section designates 1 lead story (record-breaking, billion$, war, election, etc.).
- Source line: NO tier labels (e.g. "Source: Reuters · CNBC" — never "Reuters · CNBC · T1/T2").
- TAG field: short keyword only. NO tier info in tags.
