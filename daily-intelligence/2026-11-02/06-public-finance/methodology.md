# Methodology — The Tax-to-GDP Signal: Fiscal Space or Composition Effect?

**Edition:** 2026-11-02  \n**Status:** Independent analysis, primary-source snapshot.

## Research question

How much does a hypothetical GDP shock change receipts at an unchanged tax-to-GDP ratio—and what if the ratio shifts?

## Official observations and trigger

Eurostat’s 29 October release reported EU tax and net social contributions at 40.7% of GDP in 2025, up from 40.2% in 2024. Denmark recorded 44.3% and Sweden 41.2% in 2025.

- EU 2024: **40.2 %**
- EU 2025: **40.7 %**
- EA20 2024: **40.7 %**
- EA20 2025: **41.3 %**
- Sweden 2024: **41.8 %**
- Sweden 2025: **41.2 %**
- Denmark 2025: **44.3 %**

## Reproducible model

Reference receipts = hypothetical GDP × published 2025 tax-to-GDP ratio. Scenario receipts = GDP × (1 + nominal GDP shock) × (reference ratio + ratio shift). Change = scenario receipts − reference receipts. This is a mechanical accounting counterfactual, not a structural tax elasticity estimate.

**Worked example:** Illustrative worked example: at a hypothetical €500bn nominal GDP and the published EU 40.7% tax-to-GDP ratio, a 2% nominal GDP decline with an unchanged ratio mechanically reduces receipts by €4.07bn.

All user controls are hypothetical analyst-defined inputs. Recalculate in browser by changing the controls; the model is contained in the self-contained `index.html`. The data snapshot is in `data.json`.

## Limitations and validation boundaries

The published tax-to-GDP ratio includes taxes and net social contributions; it is not a marginal tax rate. EU, EA20, Denmark and Sweden are not interchangeable jurisdictions. All GDP levels and shocks are illustrative and are not forecasts or budget projections.

## Management decision

Separate cyclical revenue sensitivity from policy, compliance, base and composition effects. Evaluate expenditure commitments and debt-service dynamics before interpreting a tax-ratio increase as fiscal space.

## Sources

- [Eurostat · Tax-to-GDP release · 29 Oct 2026](https://ec.europa.eu/eurostat/en/web/products-eurostat-news/w/ddn-20261029-3)
- [Eurostat · Government finance dataset gov_10a_taxag](https://ec.europa.eu/eurostat/databrowser/view/gov_10a_taxag/default/table?lang=en)

