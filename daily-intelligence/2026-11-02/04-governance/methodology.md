# Methodology — Tokenised Collateral: Speed Is Not the Same as Liquidity

**Edition:** 2026-11-02  \n**Status:** Independent analysis, primary-source snapshot.

## Research question

What usable collateral remains after market haircuts, legal holdbacks and delayed mobilisation?

## Official observations and trigger

On 26 October Finanstilsynet highlighted ESMA’s call for evidence on tokenised collateral at CCPs. Stakeholder responses are due 15 January 2027.


## Reproducible model

Usable collateral = nominal × (1 − market haircut) × (1 − legal/operational holdback) × (1 − adverse daily move)^delay days. Coverage = usable collateral / illustrative margin requirement. Compounding is a transparent hypothetical stress convention, not a regulatory formula.

**Worked example:** Illustrative worked example: €100m collateral with a 6% market haircut, 8% operational/legal holdback and 1.5% daily adverse move for two days produces approximately €83.91m usable value, or a €6.09m shortfall against a hypothetical €90m requirement.

All user controls are hypothetical analyst-defined inputs. Recalculate in browser by changing the controls; the model is contained in the self-contained `index.html`. The data snapshot is in `data.json`.

## Limitations and validation boundaries

ESMA is gathering evidence; the consultation does not establish new collateral eligibility or haircut rules. Every monetary value, haircut, delay and adverse price move in this dashboard is illustrative and not calibrated to any CCP or tokenised asset.

## Management decision

Require legal finality, custody segregation, operational fallback and liquidity testing before treating tokenised collateral as equivalent to immediately available traditional collateral.

## Sources

- [Finanstilsynet · CCP collateral consultation · 26 Oct 2026](https://www.finanstilsynet.no/nyhetsarkiv/horinger/2026/esma-ber-om-faktagrunnlag-tokenisering-av-sikkerheit-som-blir-stilt-overfor-sentrale-motpartar-ccp/)
- [ESMA · Call for evidence · 9 Oct 2026](https://www.esma.europa.eu/press-news/esma-news/esma-seeks-evidence-use-tokenised-collateral-central-clearing)

