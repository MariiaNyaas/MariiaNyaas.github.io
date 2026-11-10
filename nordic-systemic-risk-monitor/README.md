# Nordic Financial Resilience Monitor

## Status
Public research-stage monitoring infrastructure. Coverage: NOR, SWE, DNK, FIN, ISL. Published code does **not** claim validated early-warning predictive performance.

## Automated source update
GitHub Actions: `.github/workflows/nordic-risk-monitor.yml`; scheduled 04:35 UTC every day, plus manual dispatch and workflow-file push. Standard-library Python script `refresh.py` requests 30 country-indicator pairs from the World Bank Indicators API. It preserves prior observations on source failure, records timestamp and errors, and does not impute absent data. Each cell displays its source reference year.

## Six indicators
- `SL.UEM.TOTL.ZS`: unemployment, % of labour force.
- `FP.CPI.TOTL.ZG`: consumer-price inflation, annual %.
- `NY.GDP.MKTP.KD.ZG`: real GDP growth, annual %.
- `FS.AST.PRVT.GD.ZS`: domestic credit to private sector by banks, % of GDP (check precise metadata for indicator).
- `FB.AST.NPER.ZS`: bank non-performing loans, % of total gross loans.
- `FB.BNK.CAPA.ZS`: bank capital to assets ratio, %.

## Calculation
Unemployment: clip((u−2)/10 ×100,0,100).
Inflation: clip(abs(π)/12 ×100,0,100).
GDP: clip(−g/8 ×100,0,100).
Credit: clip((credit−40)/160 ×100,0,100).
NPL: clip(npl/15 ×100,0,100).
Capital: clip((12−capital)/12 ×100,0,100).
The index is the arithmetic mean of available components when >=4 of 6 exist. Bounds are expert-defined illustrative scales, not estimated thresholds. Factor availability changes the score denominator.

## Stress lab
Unemployment and inflation shocks are additive percentage points. Credit contraction reduces the private-credit/GDP factor proportionally. Other factors are held constant. This is arithmetic sensitivity, not a forecast or calibrated stress test.

## Independent validation still required
- Compare source vintages with primary national central-bank and supervisory releases.
- Test forecast endpoints using chronological walk-forward out-of-sample validation and alternative models.
- Verify coverage, definition changes, revision histories and cross-country comparability.
- Estimate uncertainty intervals before publishing probabilities.
- Implement independent checks against IMF Financial Soundness Indicators.

## Governance
Never display fictitious risk readings. Daily source check does not mean daily new economic data. A source outage leaves previous observations marked as stale. No use for investment or regulatory capital decisions without additional validation.
