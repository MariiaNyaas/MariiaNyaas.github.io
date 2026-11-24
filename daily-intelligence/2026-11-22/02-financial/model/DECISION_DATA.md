# Practical currency dashboard — market inputs and evidence

Snapshot prepared **24 November 2026**. Latest retained reference date:
**23 November 2026**. These are observed indicative reference quotes, not live
prices or executable dealer bid/ask quotes. The EUR/NOK forecasting experiment
remains frozen through October 2026; this market refresh does not rerun its
forecasts or establish a new forecasting advantage.

## Files

- [`../decision-data.json`](../decision-data.json): compact UI inputs, reference
  rates, selected daily/monthly history, exact FX-only historical replays,
  dated institutional facts and the published 2025 NBIM fund-value bridge.
- [`data/decision_fx_daily.csv`](data/decision_fx_daily.csv): 6,772 actual daily
  observation dates, 3 January 2000–23 November 2026, for six foreign currencies.
- [`data/decision_manifest.json`](data/decision_manifest.json): URLs, exact
  series IDs, source-retrieval times, raw download SHA-256 checksums, normalized
  CSV checksum, units, coverage, transformations and validation results.
- [`scripts/build_decision_data.py`](scripts/build_decision_data.py): collector,
  normalization and reproducible builder. Raw source caches are excluded from
  public packaging; the precise query URLs and receipts are retained.

## Normalized quotes

Every UI quote and daily CSV value is **NOK per one foreign currency unit**.

| Currency | Raw source quote, 23 Nov 2026 | Source foreign units | Normalized NOK per one unit |
|---|---:|---:|---:|
| EUR | 10.7285 | 1 | 10.7285 |
| USD | 9.8076 | 1 | 9.8076 |
| GBP | 12.8219 | 1 | 12.8219 |
| SEK | 95.47 | 100 | 0.9547 |
| CHF | 1,167.92 | 100 | 11.6792 |
| JPY | 6.1655 | 100 | 0.061655 |

The series IDs are `EXR/B.<currency>.NOK.SP`. Normalization is applied to each
row, using the row's `UNIT_MULT`:

`normalized = OBS_VALUE / 10**UNIT_MULT`.

`UNIT_MULT=2` denotes a source quote for 100 foreign units. This applies to
**CHF as well as SEK and JPY** in the retained source. English-locale thousands
separators are parsed explicitly. All 40,632 observed foreign-currency quotes
pass the raw/normalized round-trip check. The `NOK` UI entry is the arithmetic
identity 1 NOK = 1 NOK; it is not a seventh observed market series.

Norges Bank describes its rates as indicative mid-market reference rates and
states publication at approximately 16:00 local time. Its source collection
field refers to the ECB concertation reference time of 14:15. **Collection time,
publication time and download time are distinct.** The 24 November morning
snapshot therefore uses 23 November quotes.

Sources: [Norges Bank rates](https://www.norges-bank.no/en/topics/Statistics/exchange_rates/),
[API guide](https://www.norges-bank.no/en/topics/Statistics/open-data/guide-data-warehouse/),
[rate FAQs](https://www.norges-bank.no/en/topics/statistics/exchange_rates/valutakursar-faq).

## Missing values and history

The retained six-series panel contains no missing values on its common 6,772
observation dates. This does not mean every calendar day has a quote. No
weekend/holiday quotes, interpolated observations, forward fills or synthetic
cross-rates are inserted. All rates are current-source-vintage observations;
this is not a reconstruction of historical data vintages.

The compact JSON history contains the **actual last common fixing date** in
each calendar month plus the latest 120 common daily fixing dates, for 437
unique dates. The latest November observation is a **partial-month observation**,
not a completed November month-end value. The downloadable daily CSV retains
the full observed frequency.

## Historical FX-only replays

| UI label | Exact start fixing | Exact end fixing |
|---|---|---|
| February–March 2020 | 2020-02-19 | 2020-03-20 |
| February–March 2022 | 2022-02-23 | 2022-03-08 |
| April 2025 | 2025-04-01 | 2025-04-09 |

All endpoints are actual common fixing dates. A shock is the simple percentage
change `100 * (end/start - 1)`, **not a log return and not a decimal fraction**.
A positive number means more NOK are required for one foreign unit. The
reference currency NOK has an identity shock of zero.

The JSON retains start and end quotes for independent verification; all 18
foreign-currency endpoint calculations reproduce their observed end quote.
The selected windows are descriptive scenarios, not an unbiased sample of
crises or an estimate of their probabilities. They contain **no asset-price
returns, cash-flow forecasts, hedges, margin agreements or model-implied shocks**.
Applying one of these FX vectors to current or demo exposures is a hypothetical
replay, not a reconstruction of an actual historical portfolio's return.

## Policy rates

The separate `policyRates` object contains effective official policy rates as
of 23 November 2026: Norges Bank 4.50%, ECB deposit facility 2.50% and ECB MRO
2.65%. They are percentage rates per annum. ECB fixed-rate and minimum-bid MRO
series are combined only on actual matching calendar dates; all 327 overlapping
daily observations agree. These are **not** forward quotes, market funding
rates, OIS curves or policy surprises.

## Dated institutional evidence

1. **Currency translation:** NBIM's methodology presents returns in NOK and in
   the benchmark currency basket. NOK translation does not itself change the
   fund's international purchasing power. This methodological statement was
   verified on 24 November 2026.
   [Source](https://www.nbim.no/en/investments/returns/methodology-for-the-calculation-of-returns/).
2. **Liquidity from hedging:** the Financial Stability Report 2025-1 describes
   a survey of 10 Norwegian asset managers. At the end of **2025 Q1**, a
   hypothetical sudden 20% depreciation of NOK implied NOK **104 billion** of
   variation margin, with approximately NOK **680 billion** of hedged assets.
   This is a dated industry survey scenario, **not NBIM's risk, not an actual
   cash outflow and not a current estimated requirement**.
   [Source](https://www.norges-bank.no/en/news-events/publications/Financial-Stability-report/2025-1-financial-stability/web-report-2025-1-financial-stability/).
3. **Several risk dimensions:** NBIM's market-risk policy, updated 12 June 2024,
   describes absolute and relative risk through concentration, volatility and
   correlation, factors, and liquidity. This is institutional context, not a
   claim that this dashboard implements or is approved by NBIM.
   [Source](https://www.nbim.no/en/about-us/about-the-fund/governance-structure/policies/market-risk-management/).

### Published 2025 NBIM bridge

NBIM's 29 January 2026 release reports the following calendar-2025 changes in
NOK billions, rounded as published:

| Component | NOK billion |
|---|---:|
| Accounting return | +2,362 |
| Currency translation | −1,155 |
| Inflow after management costs | +319 |
| Change in fund value | +1,526 |

The bridge reconciles: `2,362 - 1,155 + 319 = 1,526`. The fund's reported
15.1% return and NOK 21,268 billion year-end value are also retained. The
15.1% return is not the percentage change in the NOK value of the fund. These
are **published historical aggregate facts**, not a current holdings dataset
or scenario assumptions.

[Source: NBIM, Strong return in 2025](https://www.nbim.no/en/news-and-insights/the-press/press-releases/2026/strong-return-in-2025/).

## Reproduce or refresh

From the research page directory, with the original source cache available:

```bash
python model/scripts/build_decision_data.py --end-date 2026-11-23
```

The script verifies and reuses cached raw downloads; if missing, it downloads
the exact source queries. To deliberately refresh that source vintage:

```bash
python model/scripts/build_decision_data.py --end-date 2026-11-23 --refresh
```

Changing the endpoint requires an explicit `--end-date`. A source refresh can
revise historical values and checksums. Preserve the frozen release before
refreshing. The builder rejects future observation dates and an attempt to
use today's FX reference date before the approximate publication time.

No user portfolio holdings, contractual hedge terms or forward bid/ask quotes
were obtained for this layer. Any demo holdings supplied by the UI remain
explicit hypothetical assumptions. The data layer makes no hedge-ratio
recommendation and assigns no probability to a stress scenario.
