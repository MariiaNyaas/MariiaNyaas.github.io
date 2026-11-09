# Methodology — Nordic Margin Transmission Test

## Data provenance
Eurostat, Euro indicators, published 5 November 2026: https://ec.europa.eu/eurostat/web/products-euro-indicators/w/4-05112026-ap. Table: domestic-market industrial producer prices, monthly changes, April–September 2026. National series are total-industry PPI, not energy PPI. All figures are transcribed from the release and are subject to revision.

## Reproducible calculations
For a monthly percent change r, the gross index multiplier is (1+r/100). April-to-September cumulative change = 100 × (product of six multipliers − 1). Spread in September = energy monthly PPI 7.8 minus ex-energy 0.1 = 7.7 percentage points. This is a component spread, NOT an estimated firm pass-through.

Hypothetical margin bridge, assuming revenue=100: energy-share e in [0,1], cost/revenue c in [0,1], price recovery p in [0,1]. Input cost change in percentage points: s=e×7.8+(1−e)×0.1. Incremental operating-profit impact as a percentage of baseline revenue: −c×s×(1−p). The illustrative profit impact is NOT a forecast. A 40% price recovery refers to 40% of the hypothetical input-cost shock and holds volume constant; it is not an estimated elasticity.

## Diagnostic design
Compare six monthly observations of energy vs non-energy and Nordic national PPI; use cumulative compounded rates and a live three-driver sensitivity model. Country data are descriptive comparators, not explanatory regressors.

## Alternative explanations and falsification
Country PPI dispersion may reflect industry composition, energy mix, contract indexation, FX, and sampling/revisions. Evidence against a narrow energy-only narrative would be persistent acceleration in ex-energy PPI or intermediate goods, or demonstrated firm-level pass-through independent of energy exposure. Confirm with matched firm invoices, hedges, energy quantities, price contracts, revenue mix and lagged cost ledgers.

## Boundaries
Six months are insufficient for lag estimation, causal identification, predictive accuracy or statistical significance. The analysis must not be used as an investment recommendation.
