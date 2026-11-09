# Methodology: The Monetary-Policy Decision Gap: How to Govern a No-Change Rate

Publication: 2026-11-09
Primary release: Norges Bank, 5 Nov 2026 — https://www.norges-bank.no/en/news-events/news/Press-releases/2026/2026-11-05-rate/

## Observed facts
- Policy rate: 4.5%
- CPI: 3.4%
- CPI-ATE: 3.0%
- Target: 2.0%

## Hypothesis
An unchanged policy rate can coexist with changing macro risks; board triggers should depend on risk limits, not the rate headline.

## Deterministic model
indicatorScore=40×max(0,CPIATE−2)/4 + 35×max(0,unemployment−2)/4 + 25×riskAppetiteScore/100 (clamped 0–100)

## Inputs
- CPI-ATE scenario: 3% (range 0–8)
- Unemployment scenario: 2% (range 0–8)
- Board risk appetite score: 55/100 (range 0–100)

## Interpretation and limitations
Weights and thresholds are explicitly arbitrary governance design assumptions; this is not Norges Bank's model.

## Competing explanation
The policy decision includes FX, labour market and energy shocks; a single inflation reading is not sufficient.

## Falsification
Backtesting of firm-level risk triggers shows no material incremental value beyond existing risk limits.

## Research status
Exploratory scenario, not causal identification, calibrated forecast, portfolio recommendation or empirical backtest. Observed indicators must not be treated as the model's calibrated parameters.
