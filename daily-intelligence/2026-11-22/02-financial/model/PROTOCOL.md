# EUR/NOK multidimensional research protocol — version 2

Protocol fixed on 24 November 2026 before running the expanded model comparison.
The historical observations were already public. This is a latest-vintage,
pseudo-out-of-sample study, not an untouched historical experiment.

## Question and estimands

Does information about relative policy rates, oil, global risk and relative
macroeconomic conditions improve forecasts of **end-of-month** EUR/NOK changes?
Does the rate block add information after controlling for the other blocks?
How stable are those answers across horizons and observable market regimes?

The target is 100 × log(S[t+h] / S[t]), where S is NOK per EUR at the last
available Norges Bank daily fixing in the month and h is 1, 3 or 6 months.
Positive returns mean NOK depreciation. Indicative fixings are not executable
trading prices. The original monthly-average experiment is retained separately.

## Data and information set

- Completed months only, with an initial cutoff of 31 October 2026.
- Norges Bank policy rate and ECB deposit facility / MRO rates: month-end.
- EUR/NOK momentum and trailing volatility: observable through the origin.
- EIA Brent, VIX and the Fed broad dollar index: lagged by **one full month**
  to allow for public dissemination and different daily fixing times.
- Eurostat HICP and industrial-production comparisons: lagged by **two months**.
- No interpolation, backfill or forward-fill of market or macro observations.
  Policy effective dates may be carried only within a source's observed coverage.
- Macro and dollar-index historical revisions remain a limitation even after
  imposing release lags. No claim of a vintage-correct real-time backtest.
- Public ECB announcement surprises, if downloaded, are a separate extension.
  Missing Norwegian OIS/FRA surprises are not replaced by policy-rate changes.

## Models declared before scoring

1. Zero-return random walk.
2. AR(1): own previous monthly return, with an intercept.
3. AR(1) plus Norwegian policy-rate level and monthly change.
4. AR(1) plus Norway–ECB deposit-rate differential, its change, and the ECB
   MRO–deposit corridor. These are administered rates, not OIS expectations.
5. Relative-rate model plus lagged one- and three-month Brent changes.
6. Previous model plus lagged log VIX, VIX change, broad-dollar return and
   trailing six-month EUR/NOK volatility.
7. Full model: previous model plus lagged HICP and industrial-production gaps.
8. Full model plus two prespecified stress interactions (rate gap × stress;
   oil change × stress), where lagged VIX >= 25 defines stress.
9. Fixed conservative ensemble: 50% random walk, 25% AR(1), 25% full model.

The multivariate models use ridge regression with alpha=10 after standardising
features within each training window; the intercept is not penalised. AR(1)
uses OLS. No hyperparameters or ensemble weights are selected on the evaluation
sample. Each non-baseline model is re-estimated at every origin.

## Validation and uncertainty

- Expanding training windows; at least 60 fully observed labelled rows.
- Common complete feature sample and common forecast origins across models.
- First eligible evaluation origin no earlier than January 2015.
- Direct h-month targets; a training row is eligible only when its target
  month is no later than the forecast origin. This purges immature labels.
- MAE, RMSE, direction accuracy and paired loss improvements against both
  random walk and AR(1); no profitability claim from direction accuracy.
- Circular block bootstrap, 3,000 draws, block length max(3,h); longer-block
  sensitivity max(6,2h). Report 95% intervals for paired mean MAE differences.
- Approximate two-sided centred-block bootstrap p-values; Holm adjustment
  across the declared comparisons against random walk and AR(1), over all
  three horizons. Intervals remain descriptive marginal intervals.
- Drop-one-block ablations on the **same** sample, independently refitted:
  rates, energy, risk and macro. Their intervals are exploratory; they do not
  form a separate claim of discovery.
- Prediction bands use only previously matured out-of-sample errors (latest
  60, at least 24). Empirical 5th/95th percentiles are not guaranteed coverage.
- Risk, relative-rate, oil and calendar subperiod diagnostics are descriptive;
  small subsamples are marked and no regime is chosen after seeing scores.

## Economic use and boundaries

The conditional scenario tool changes model inputs and recomputes an association.
It does not identify the causal effect of a rate decision. Joint scenarios may
be out of the historical data support; feature-range flags must be displayed.
The treasury calculator uses explicit user-entered exposure, hedge ratio and
forward-rate assumptions. It is not evidence of a profitable hedge or trade.

All outputs must distinguish available data, documented proxies and unavailable
licensed inputs. Reproducibility includes retrieval URLs, series identifiers,
observation windows, hashes, transformations and model code.

## Prospective test

The first genuinely prospective month-end origin after this protocol is
30 November 2026. Its subsequent forecasts must be saved before outcomes mature.
The October snapshot generated in November must not be described as a forecast
that was actually made in October. No live strategy is promoted on backtest fit.
