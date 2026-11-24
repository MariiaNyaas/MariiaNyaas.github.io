# EUR/NOK Research Lab — version 2.0

Research frozen on 24 November 2026; completed-month cap: **October 2026**.

**Decision:** retain the random walk as the operational reference. The full model is useful for diagnostics and explicit conditional scenarios, but has not demonstrated a robust forecast advantage. No trading strategy or dependable risk limit has been established.

## Read the research

- [Dashboard](../dashboard.html), [English methodology](../methodology-v2.html), [Russian note](RESEARCH_NOTE_RU.md).
- [Frozen protocol](PROTOCOL.md), [original monthly-average experiment](https://mariianyaas.github.io/daily-intelligence/2026-11-22/02-financial/original.html).
- [Results](output/results.json), [full comparison CSV](output/model_comparison.csv), [audit](output/audit.json).

## Actual results

MAE in percentage points of log EUR/NOK return; lower is better.

| Horizon, months | Origins | Random walk | AR(1) | Full | Fixed ensemble |
|---:|---:|---:|---:|---:|---:|
| 1 | 141 | 2.033 | 2.012 | 2.157 | 2.038 |
| 3 | 139 | 2.826 | 2.804 | 3.083 | 2.798 |
| 6 | 136 | 3.578 | 3.580 | 4.170 | 3.448 |

Full-model improvement intervals versus random walk: 1m: [-0.293, +0.036]; 3m: [-0.648, +0.126]; 6m: [-1.411, +0.215] pp. All include zero; no declared advantage survives the 45-comparison Holm adjustment. The full model's six-month empirical 5th/95th residual band covered **74/107 = 69.16%**, not a dependable 90%.

## Design

The monthly panel contains 11 observed series; the full model uses 12 derived features. Nine models are compared at 1/3/6 months. The common feature sample begins 2006-03. Evaluation uses expanding windows from 2015-01, identical samples, at least 60 mature labels and direct-horizon targets. A label is eligible only when its target month is no later than the forecast origin.

The target uses the last Norges Bank daily fixing of each month, not a monthly average. Original and v2 MAEs therefore are not a before/after performance comparison. Positive log EUR/NOK returns mean NOK depreciation.

Policy/FX inputs are available through the origin; Brent, VIX and broad USD inputs are lagged one month, and HICP/industry inputs two months. Latest-vintage revisions remain a limitation. Standardisation uses training data only; multivariate ridge alpha=10 and ensemble weights (50% RW, 25% AR1, 25% full) are fixed. Four independently refitted ablations remove rates, energy, risk or macro. Circular-block bootstrap: 3,000 draws; length max(3,h), sensitivity max(6,2h). Ablations and regimes are exploratory.

## Reproduce the frozen numerical model

Verified environment: **Python 3.12.14, NumPy 2.3.5, pandas 2.2.3**. The optional ECB workbook collector also uses **openpyxl 3.1.5**. No scikit-learn or statsmodels is required.

From this `model` directory, using the retained normalised inputs and manifests:

```bash
python scripts/run_model.py
```

This writes forecast results, comparisons, feature data, snapshot values and chronological predictions. Generated timestamps change on rerun; numerical values should reproduce with the stated versions and unchanged inputs/protocol. The script is [run_model.py](scripts/run_model.py).

## Retrieve sources and run source-dependent modules

Public packaging excludes raw vendor quote dumps. Normalised inputs, their provenance and analytical outputs are retained. Source auditing and the event module additionally require the original raw records. In a separate working copy, retrieve them with the supplied collectors:

```bash
python scripts/collect_market.py
python scripts/collect_macro.py
python scripts/run_model.py
python scripts/run_event_study.py
python scripts/audit_model.py
```

The collectors reuse cached raw records when available. A deliberate refresh is optional:

```bash
python scripts/collect_market.py --refresh
python scripts/collect_macro.py --refresh
```

**A refresh can retrieve revised history.** Its output is a new source vintage and may no longer reproduce the frozen results or hashes. Defaults retain the October 2026 observation cap; refreshing does not silently advance the research horizon. Preserve the frozen package before running collection. Source reuse/redistribution remains subject to the publishers' terms.

- [Market collector](scripts/collect_market.py), [macro/ECB collector](scripts/collect_macro.py).
- [Event module](scripts/run_event_study.py), [independent audit code](scripts/audit_model.py).
- The recorded audit passed eight groups in the same research session: source integrity, calendar/quote identity, mature labels/common samples, metric/ablation/scenario arithmetic, band maturity/coverage, multiplicity/timestamps, input timing perturbations and truncated-history reproduction. This is not an external audit or peer review.

## Historical ECB event module

The retained EA-MPD workbook is updated 4 November 2025 and ends 30 October 2025. It is excluded from the current complete-sample forecast block. The module uses one prespecified tenor (OIS1Y), one window (Monetary Event Window), a baseline fixing strictly before each event and outcomes at the first/fifth/twentieth fixing strictly after it.

| Subsequent fixings | Events | Association per +10 bp, % | Bonferroni interval, % |
|---:|---:|---:|---:|
| 1 | 292 | +0.246 | [-0.014, +0.527] |
| 5 | 292 | +0.354 | [-0.117, +1.035] |
| 20 | 292 | +0.431 | [-0.221, +1.115] |

All Bonferroni 98.333% per-horizon intervals include zero. The nominal three-horizon family confidence is 95%; dependence and exploratory-inference limitations remain. Twenty-fixing windows overlap for 148 adjacent event pairs. OIS repricing includes guidance/information and is not equivalent to a policy-rate hike. No causal identification or trading profitability follows.

## Files and provenance

| Artifact | Purpose |
|---|---|
| [market.csv](data/market.csv), [macro.csv](data/macro.csv) | Frozen observation-dated inputs; missing values retained |
| [features.csv](data/features.csv) | Transformed, information-lagged feature matrix |
| [market_manifest.json](data/market_manifest.json), [macro_manifest.json](data/macro_manifest.json) | URLs, exact series, units, coverage, hashes and retrieval metadata |
| [predictions.json](output/predictions.json), [ablation_predictions.json](output/ablation_predictions.json) | Origin/target dates, forecasts and paired audit records |
| [history.json](output/history.json), [snapshot_forecasts.csv](output/snapshot_forecasts.csv) | Dashboard input history and October snapshot |
| [ea_mpd_events.csv](data/ea_mpd_events.csv), [ea_mpd_manifest.json](data/ea_mpd_manifest.json) | Observed ECB event inputs and actual file coverage |
| [event_study.json](output/event_study.json), [event_observations.csv](output/event_observations.csv) | Event regression, uncertainty and exact fixing-date pairs |

Official references: [Norges Bank FX](https://www.norges-bank.no/en/topics/Statistics/exchange_rates/), [ECB rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html), [EIA Brent via FRED](https://fred.stlouisfed.org/series/DCOILBRENTEU), [Cboe VIX via FRED](https://fred.stlouisfed.org/series/VIXCLS), [Federal Reserve broad USD](https://fred.stlouisfed.org/series/DTWEXBGS), [Eurostat HICP](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table?lang=en), [Eurostat industry](https://ec.europa.eu/eurostat/databrowser/view/sts_inpr_m/default/table?lang=en), [ECB EA-MPD](https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx).

## Remaining data and prospective gate

Unacquired inputs are Norway/EA OIS and FRA curves and Norwegian announcement surprises, consensus forecasts with release timestamps, historical real-time vintages, and executable forward quotes/spreads. Ordinary policy changes do not replace surprises. No paid data was purchased.

EA20 is fixed-composition, Norwegian industry includes extraction, and HICP methodology may change at January 2026. Scenario associations and user-entered treasury assumptions are not causal forecasts or executable hedge recommendations.

The October snapshot was calculated **24 November 2026**, not issued in October. The first genuinely prospective origin after the protocol freeze is **30 November 2026**. Store its forecasts before subsequent outcomes mature. **No automated monthly scheduler is configured.**
