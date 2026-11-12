# The Depreciation Illusion

Six supplied SEC Company Facts JSON documents. USD units only; filings dated no later than 12 November 2026. Annual cash flows require form 10-K and duration 330–380 days. Deduplicate each issuer/concept/end date using the latest eligible filing and accession, resolving tag migrations separately for each period. Alternative tags are not added. Retain concept, period start/end, filing date and accession. The output is a latest-vintage historical series, not an as-originally-reported point-in-time panel; consequently no pseudo-real-time securities backtest is claimed. CFO, net income and cash investment are annual flows; assets are period-end stock. D&A tags have differing coverage and are shown explicitly. Cohort scenarios use straight-line zero-to-user-defined salvage allocation and an assumed economic replacement horizon. They do not estimate a historical depreciation bias.

## Limits

No comparable compute-only asset cohort panel, maintenance-capex split, chip utilisation, lease-adjusted total investment or independent resale data. Issuer fiscal calendars differ. SEC taxonomy does not establish that all capex serves AI. No regression estimates an economic useful life. Accounting or valuation conclusions require the underlying audited notes.

## Equations

Compute cohort = total cohort × compute share.
Annual book allocation = (compute cohort − salvage) / book life.
Annual economic replacement proxy = (compute cohort − salvage) / replacement horizon.
After-tax gap = (replacement proxy − book allocation) × (1−effective tax).
This is a user-defined cohort scenario, not a company earnings restatement.

## Reproduction

Run `python analyze.py /path/to/the/28/source/files` with Python 3, numpy, pandas, scipy and openpyxl. The analysis does not access the network. Results use a latest-available vintage as of 12 November 2026. A historical holdout formed from revised observations is a chronological validation, not a true real-time vintage backtest.

## Falsification

- Cohort-level evidence that older compute generates sufficient net cash after energy costs for longer than the assumed replacement horizon.
- Verified workload migration, resale or retirement data showing consistently shorter economic lives.
- Reconciled lease additions and maintenance investment materially changing the apparent funding gap.