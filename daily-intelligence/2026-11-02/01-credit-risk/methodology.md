# Methodology — Norway’s Mortgage Risk Is Moving Towards the Boundary

**Edition:** 2026-11-02  \n**Status:** Independent analysis, primary-source snapshot.

## Research question

How much borrower equity remains after a housing correction when lending shifts closer to the 90% LTV limit?

## Official observations and trigger

Finanstilsynet published its 2026 mortgage lending survey on 29 October. The weighted average debt-to-income ratio rose to 333% from 329% in 2025, while first-time buyers’ average LTV rose to 79% from 77%.

- All borrowers DTI 2025: **329 %**
- All borrowers DTI 2026: **333 %**
- First-time DTI 2025: **380 %**
- First-time DTI 2026: **376 %**

## Reproducible model

Loan = home value × origination LTV. Stressed collateral value = home value × (1 − price decline). Equity buffer = stressed collateral value − loan. Stressed LTV = loan / stressed collateral value. No amortisation, recovery costs or borrower cash flow are modelled.

**Worked example:** Illustrative worked example: a NOK 5.0m home financed at 79% LTV carries NOK 3.95m of debt. A 20% price decline leaves NOK 50,000 collateral equity and produces a 98.75% stressed LTV.

All user controls are hypothetical analyst-defined inputs. Recalculate in browser by changing the controls; the model is contained in the self-contained `index.html`. The data snapshot is in `data.json`.

## Limitations and validation boundaries

Survey of approximately 12,000 new loans from 25 banks, not a full mortgage stock. Observed averages describe different cohorts. The model applies hypothetical LTV and price shocks to a single property; it is not an estimate of bank losses, PD or LGD.

## Management decision

Use origination LTV bands and stressed collateral buffers jointly, rather than relying on the average debt-to-income ratio alone. Validate results with loan-level affordability, guarantees and geographic exposures.

## Sources

- [Finanstilsynet · Mortgage survey summary · 29 Oct 2026](https://www.finanstilsynet.no/publikasjoner-og-analyser/boliglansundersokelser/2026/boliglansundersokelsen-2026/oppsummering/)
- [Finanstilsynet · Key findings · 29 Oct 2026](https://www.finanstilsynet.no/publikasjoner-og-analyser/boliglansundersokelser/2026/boliglansundersokelsen-2026/i-korte-trekk/)
- [Finanstilsynet · Sample definition · 29 Oct 2026](https://www.finanstilsynet.no/publikasjoner-og-analyser/boliglansundersokelser/2026/boliglansundersokelsen-2026/informasjon-om-boliglansundersokelsen/)

