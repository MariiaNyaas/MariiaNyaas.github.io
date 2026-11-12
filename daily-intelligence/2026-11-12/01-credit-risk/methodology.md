# The Electricity–Credit Nexus

Source: SSB 08551, all industries, total bankruptcies, Oslo code 03. Sort 226 months; do not sum county series with historical zeros. Model log(1+B_t)=a+b log(1+B_(t−1))+c sin(2πm/12)+d cos(2πm/12). Fit by OLS at each expanding origin, forecasting one month ahead over the last 36 months (2023-11–2026-10). Exponentiation gives a conditional-median count forecast, without a lognormal mean correction. Compare against B_(t−12); report MAE/RMSE. Full-sample coefficient intervals use Bartlett Newey–West covariance with 12 lags. No electricity regressor enters this baseline. The sector price scenarios are arithmetic, not estimated PD forecasts.

## Limits

No firm-level energy exposure, outstanding-credit denominator, borrower failure panel or matched hedge information. Covid-era policy and insolvency changes are potential breaks. Baseline forecast evaluation uses a single holdout; specification selection was not preregistered. No causal or nationwide predictive validation is claimed.

## Equations

EBITDA_stress = revenue × margin − revenue × energy_share × price_shock × (1−hedge) × (1−pass_through) − revenue × output_loss × margin.
Debt_service = debt × rate + scheduled_principal.
Coverage = EBITDA_stress / debt_service. This simplified covenant proxy is not cash DSCR: tax, working capital and maintenance capex are excluded.

## Reproduction

Run `python analyze.py /path/to/the/28/source/files` with Python 3, numpy, pandas, scipy and openpyxl. The analysis does not access the network. Results use a latest-available vintage as of 12 November 2026. A historical holdout formed from revised observations is a chronological validation, not a true real-time vintage backtest.

## Falsification

- A matched firm-level panel linking electricity invoices and contracts to arrears/defaults, with pre-shock exposure and a credible comparison group.
- A geography-consistent multi-year price panel and rolling tests showing improvement over rates, sector and macro controls.
- Evidence that physical curtailment, rather than energy costs, dominates borrower cash losses.