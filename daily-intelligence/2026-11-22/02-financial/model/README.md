# Currency Risk & Treasury Decisions — version 3.0

**Current canonical page:** [decision dashboard](https://mariianyaas.github.io/daily-intelligence/2026-11-22/02-financial/).

This release replaces the former standalone policy-rate study at the same address. The original page/archive and obsolete download have been withdrawn. Existing `dashboard.html` and `methodology-v2.html` links route to the current product and methods. Frozen numerical evidence is retained as supporting research, with its own original version and hash.

## Research question and decision

How can a treasury or portfolio team make a defensible currency decision when a reliable directional forecast advantage has not been established?

The answer is a transparent combination of observed currency evidence, explicit exposure and contract data, budget constraints, policy comparisons, reverse stress and separate collateral sensitivity. The dashboard distinguishes current market observations, dated public facts, hypothetical examples, user-supplied contracts and statistical research results.

No validated trading edge, calibrated probability of budget breach, complete dealer valuation or institution-specific hedge recommendation is claimed. The useful outputs are consequences and feasible policies under stated assumptions. Current policy is the decision comparator; random walk remains a forecasting comparator only.

## Current evidence

Latest Norges Bank reference observations: **23 November 2026**. Snapshot retrieved **24 November 2026**. Every rate is NOK per **one** foreign unit:

| EUR | USD | GBP | SEK | CHF | JPY |
|---:|---:|---:|---:|---:|---:|
| 10.7285 | 9.8076 | 12.8219 | 0.9547 | 11.6792 | 0.061655 |

The full daily panel contains 6,772 observed dates and 40,632 foreign-currency observations from January 2000. CHF, SEK and JPY source quotes are per 100 units; `UNIT_MULT` normalization is explicit. NOK=1 is an arithmetic identity, not an additional observed currency series. Reference rates are indicative, not executable prices. The November history endpoint is a partial-month observation.

Three historical FX-only replay windows preserve exact observed start/end quotes. They do not invent equity/bond returns or reconstruct a user's historical contracts. The data also retain the observed 2025 NBIM bridge: NOK 2,362bn accounting return − 1,155bn currency translation + 319bn net inflow = 1,526bn increase in fund value. The 2025 Q1 collateral survey is labelled as a hypothetical stress reported by ten other Norwegian managers, not NBIM's margin requirement.

[Full data provenance](DECISION_DATA.md) · [decision input JSON](../decision-data.json) · [daily FX CSV](data/decision_fx_daily.csv) · [source manifest](data/decision_manifest.json).

## Decision arithmetic

Treasury cash cost is signed: payable positive, receivable negative. With original amount A, scenario realised amount Q, fixed hedged amount H, budget rate B, contract rate F and settlement rate S:

`signed cash cost = direction × [Q × S + H × (F − S)]`.

Budget, volume, FX and hedge effects reconcile exactly. A forecast-volume shock does not resize a contract, so cancellation can create overhedging. Settlement dates and entity information remain in the cash-flow timeline. Aggregation does not imply legal netting or frictionless intercompany cash transfers.

Reverse stress solves a linear budget constraint and returns a feasible hedge interval, an upper bound or no feasible policy as appropriate. A common-FX boundary is a specified joint shock. Alternative policies are counterfactual comparisons at the supplied forward terms, not executable unwind offers.

Portfolio return retains the multiplicative interaction:

`(1 + local asset return) × (1 + FX return) − 1`.

The local-asset, currency, interaction and fixed-unit hedge effects reconcile to scenario NAV. The currency-policy benchmark uses the same positions with a stated hedge share; it is not the actual GPFG benchmark. Currency of denomination is not a complete economic look-through exposure for a multinational company.

Collateral is a separate liquidity calculation. Explicit stressed forward marks are supported. The fallback is a clearly labelled undiscounted settlement-payoff proxy, not a dealer mark-to-market. Offsetting is limited to supplied entity/netting-set groups. Thresholds, posted collateral, eligible collateral, haircuts, cash and facilities are explicit assumptions. Immediate collateral and terminal settlement cash are not added as if both were permanent losses.

[Detailed methodology](../methodology.html) · [engine API and assumptions](DECISION_ENGINE.md) · [decision engine](../decision-engine.js).

## Use and reproduce

Open the published page, or serve the extracted research directory with a static HTTP server. Browser fetch restrictions can prevent a `file://` page from loading JSON inputs.

```bash
python -m http.server 8000
```

Example books are explicitly illustrative. CSV import and saved-scenario JSON use the browser's local file interface; they are not uploaded to a research server. Check import errors before replacing a book. A scenario save contains the supplied book and assumptions; treat the exported file accordingly. A print view prepares a decision memo with provenance and limitations.

Run decision-engine verification from this `model` directory:

```bash
node scripts/test_decision_engine.cjs
```

The engine has no third-party JavaScript dependencies. To rebuild the observed decision dataset from retained raw cache or the precise source queries:

```bash
python scripts/build_decision_data.py --end-date 2026-11-23
```

`--refresh` deliberately retrieves a new vintage; an explicit later end date advances the observation cutoff. Revised history may change hashes. Refreshing market data does not re-estimate the frozen monthly forecasting experiment.

## Frozen forecasting evidence

The preserved statistical protocol was frozen on 24 November 2026, with completed-month observations through October 2026. It uses 11 raw series, 12 full-model factors, nine specifications and 1/3/6-month direct forecasts. Common features begin March 2006; expanding-window evaluation starts January 2015. Only matured labels are eligible. Train-only scaling, ridge alpha=10 and ensemble weights (50% random walk, 25% AR1, 25% full) are fixed.

| Horizon | Origins | Random walk MAE | AR(1) | Full | Fixed ensemble |
|---:|---:|---:|---:|---:|---:|
| 1 month | 141 | 2.0335 | 2.0116 | 2.1572 | 2.0385 |
| 3 months | 139 | 2.8258 | 2.8044 | 3.0834 | 2.7982 |
| 6 months | 136 | 3.5776 | 3.5801 | 4.1699 | 3.4481 |

MAE units: percentage points of cumulative log EUR/NOK return. All candidate improvement intervals against random walk include zero. No advantage survives 45-comparison Holm adjustment. Full-model six-month residual-band coverage is **74/107 = 69.16%**; a 5th–95th percentile construction is not a dependable 90% future risk limit. Latest-vintage macro revisions remain a limitation.

The October model output was calculated on 24 November, not issued in October. The first prospective origin after the freeze is **30 November 2026**. No automated monthly scheduler is configured.

Numerical reproduction with retained normalized inputs:

```bash
python scripts/run_model.py
```

Verified statistical runtime: Python 3.12.14, NumPy 2.3.5, pandas 2.2.3; optional ECB workbook collector openpyxl 3.1.5. Source-dependent audits and the historical ECB event module require the raw records, retrievable with `collect_market.py` and `collect_macro.py`. A source refresh can revise historical observations.

The ECB event study has 292 matched historical events through October 2025; all three Bonferroni-adjusted intervals include zero. Its OIS repricing is not equivalent to an isolated policy-rate change, and it is not a current forecast feature.

## Validation and release

- [Decision-engine tests](output/decision_validation.json): financial identities, signs, boundary conditions, cancellation, portfolio interaction, netting isolation and input validation.
- [Source manifest](data/decision_manifest.json): unit roundtrips, exact history/replay identities, source receipts and hashes.
- [Frozen statistical audit](output/audit.json): eight groups covering source identity, chronology, matched samples, arithmetic, interval maturity, multiplicity, perturbations and truncated-history reproduction.
- [Release manifest](release_manifest.json): exact packaged files and SHA-256 hashes.

Checks are performed within the research session; they do not constitute external peer review. Actual exposures, legally enforceable agreements and executable contract quotes are necessary for institution-specific deployment. No paid quote dataset or private institutional holdings have been inferred or substituted.

Package the current page, normalized inputs, documentation, code and outputs:

```bash
python scripts/package_release.py
```

The resulting `currency-risk-decisions.zip` excludes raw provider caches. Original source queries, receipts and rights notes remain in the manifests.
