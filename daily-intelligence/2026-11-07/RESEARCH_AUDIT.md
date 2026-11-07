# Research validation note — 2026-11-07

Status: **revised exploratory publication; not independently certified institutional research**.

## Scope
Six research dashboards have been updated to include a second, decision-oriented two-factor scenario laboratory. All scenario inputs are explicitly hypothetical; they are not causal estimates, confidence intervals or probability-weighted forecasts.

## Credit risk correction
- Source: Statistics Norway, table **09560**, bank loans to **non-financial corporations** at December year-end; annual percentage growth, 1998–2025. Bankruptcy counts: table **09695**, summed by calendar year.
- Same-year OLS, HAC standard errors with 2 lags, 28 annual observations: coefficient **−57.0166** bankruptcies per percentage point; 95% HAC confidence interval **[−64.7006, −49.3326]**; R² **0.5549**.
- One-year-lag OLS, 27 observations: coefficient **−32.9623**, p ≈ **0.0194**, R² ≈ **0.1944**.
- Two-year-lag OLS, 26 observations: coefficient **−2.7363**, p ≈ **0.8032**, R² ≈ **0.00144**.
- Expanding-window out-of-sample test of the **one-year-lag model**: RMSE ≈ **515.1** bankruptcies versus ≈ **564.9** for a historical-mean baseline. Small sample, macro confounding and structural instability limit generalisation.
- Previous displayed contemporaneous coefficient of −69.075 and R²≈0.61 have been corrected in the research page. Historical credit-growth values were replaced with a source-consistent annual series.

## Additional source checks
- SSB **09560** December 2025 total bank loans: NOK **5,175,321 million**. SSB **09565** December 2025 total bank deposits: NOK **5,095,123 million**. Simple ratio: **101.57%**; not a liquidity regulatory ratio.
- SSB **13662** 2026 initial government R&D appropriation: NOK **50,276 million**, nominal.
- SSB **14708** annual index-based 2025 inflation: CPI ≈ **3.06%**, CPI-ATE ≈ **3.08%**.
- SSB **07251** manufacturing labour cost 2025 annual index rebased to 2010: **158.56**. SSB **12462** manufacturing PPI similarly rebased: **191.76**.
- SSB **14091** electricity annual quantities do not establish peak-load adequacy or grid capacity.

## Outstanding limitations
1. Independent end-to-end browser testing, JavaScript runtime testing, and GitHub Pages deployment verification are not completed by this audit.
2. No comprehensive independent source-by-source replication of every historical series is certified here.
3. Scenario matrices are deterministic accounting sensitivities; most have no estimated behavioural feedback, probabilistic calibration, or external validation.
4. No causal identification, full structural macro model, or production-grade portfolio capital allocation framework is claimed.
5. Any future institutional release should publish raw source extracts, exact processing scripts, unit tests, data vintage, and model governance sign-off.

**Editorial rule:** never equate attractive interactive charts with investment-grade empirical evidence.
