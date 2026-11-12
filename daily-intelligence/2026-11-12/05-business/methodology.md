# Europe’s AI Adoption Paradox

Eurostat isoc_eb_ai Sheet 9: enterprises with 10+ employees using at least one AI technology, percentage, annual observations 2021/2023/2024/2025. Size comparison uses Sheets 1, 13 and 17; SMEs are not added to their component size classes. Productivity is nama_10_lp_ulc Sheet 2: real labour productivity per hour, index 2015=100. Join exact country labels for 27 EU members; exclude EU/euro-area aggregates, non-EU states and missing pairs. Growth_2025=100×(index_2025/index_2024−1). Estimate unweighted OLS growth_2025=a+b adoption_2024 with HC3 covariance and asymptotic normal 95% intervals. Check Spearman rank association and leave-one-country-out slopes. Temporal holdout: estimate 2024 growth on 2023 adoption, freeze coefficients, predict 2025 growth from 2024 adoption; compare RMSE with the 2024 cross-country mean. Countries are not assumed independent experimental units; HC3 addresses heteroskedasticity, not regional spillovers. Flags are retained in downloadable normalized files.

## Limits

Only a few adoption survey waves; no causal identification or long-run panel. Macro productivity and enterprise-survey populations differ. Small n, revisions, country outliers and cross-country dependence limit inference. One held-out year is not evidence of durable forecasting power. No “no effect” conclusion follows from a large p-value.

## Equations

Gross contribution_pp = adoption_fraction × task_fraction × utilisation_fraction × task_uplift_pct × (1−leakage) × (1−displacement).
Net contribution_pp = gross contribution_pp − implementation_drag_pp.
This is a transparent scenario accounting identity, not a regression forecast or GDP projection.

## Reproduction

Run `python analyze.py /path/to/the/28/source/files` with Python 3, numpy, pandas, scipy and openpyxl. The analysis does not access the network. Results use a latest-available vintage as of 12 November 2026. A historical holdout formed from revised observations is a chronological validation, not a true real-time vintage backtest.

## Falsification

- Matched firm-level evidence with credible controls demonstrating persistent productivity gains net of implementation costs.
- Several additional survey waves showing stable out-of-sample improvement over sector/macro baselines.
- Revisions or intensity-weighted adoption measures changing the cross-country relationship.