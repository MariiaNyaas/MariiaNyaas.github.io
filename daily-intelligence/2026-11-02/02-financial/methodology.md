# Methodology — The ECB Hold and the Two-Sided Margin Squeeze

**Edition:** 2026-11-02  \n**Status:** Independent analysis, primary-source snapshot.

## Research question

Can a bank preserve net interest income if its deposit beta rises while the policy-rate path remains uncertain?

## Official observations and trigger

On 29 October the ECB kept deposit, main refinancing and marginal lending rates at 2.50%, 2.65% and 2.90%. It warned that higher energy prices could lift inflation and weaken growth.

- Deposit facility: **2.5 %**
- Main refinancing: **2.65 %**
- Marginal lending: **2.9 %**
- HICP Sep 2026: **3.8 %**

## Reproducible model

Illustrative annual ΔNII (€m) = rate shock (bp)/10,000 × [rate-sensitive assets × asset beta − rate-sensitive liabilities × liability beta]. The model is a first-order sensitivity, not a forecast or a bank-specific asset-liability model.

**Worked example:** Illustrative worked example: €1.5bn of assets, €1.3bn of liabilities, a +100bp parallel shock, 50% asset beta and 65% deposit beta yield −€0.95m annual ΔNII. The deposit beta break-even is approximately 57.7%.

All user controls are hypothetical analyst-defined inputs. Recalculate in browser by changing the controls; the model is contained in the self-contained `index.html`. The data snapshot is in `data.json`.

## Limitations and validation boundaries

All balance-sheet amounts, betas and shocks are hypothetical. Parallel instantaneous repricing assumes a one-year static balance sheet, no hedges, floors, behavioural deposits, credit migration or FX. September HICP is an earlier release and is not an October flash estimate.

## Management decision

Monitor deposit and asset repricing betas alongside stress-driven liquidity migration. Avoid extrapolating the ECB’s unchanged decision into a forecast of future rates.

## Sources

- [ECB · Monetary policy decisions · 29 Oct 2026](https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp261029~9a493adf17.en.html)
- [Eurostat · September HICP · 16 Oct 2026](https://ec.europa.eu/eurostat/en/web/products-euro-indicators/w/2-16102026-ap)

