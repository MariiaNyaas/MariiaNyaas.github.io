# Methodology — ESRS-40a: From Reporting Scope to Audit-Ready Evidence

**Edition:** 2026-11-02  
**Status:** Independent analysis, primary-source snapshot and synthetic scenario.

## Research question

Which evidence-control gaps should a cross-border reporting team remediate before assurance planning?

## Official observations and trigger

EFRAG held its final ESRS-40a outreach event on 29 October 2026, ahead of the 31 October consultation deadline for certain non-EU undertakings. The cited sources describe consultation and enforcement context; they do not establish the effectiveness of any individual undertaking's reporting controls. The consultation material should not be treated as adopted law.

## Reproducible model

**Illustrative diagnostic score** = Σ(weight_i × status_factor_i), where Ready = 1, Partial = 0.5 and Missing = 0.

The analyst-defined weights total 100 points:

| Control | Weight |
| --- | ---: |
| Scope mapping | 15 |
| Entity boundaries | 15 |
| Materiality rationale | 10 |
| IRO-to-metric linkage | 15 |
| Data lineage | 15 |
| Control owners | 10 |
| Report cross-references | 10 |
| Assurance trail | 10 |
| **Total** | **100** |

The weights and status factors are illustrative analyst assumptions, not regulatory parameters or an assurance standard. The score is an internal scenario diagnostic only; it does not quantify ESRS compliance or verified audit readiness.

**Worked example:** Under the synthetic default scenario, Scope mapping (15 × 0.5 = 7.5), Materiality rationale (10 × 0.5 = 5), Data lineage (15 × 0.5 = 7.5) and Control owners (10 × 1 = 10) contribute 30 points in total. The other four controls are Missing and contribute zero. The resulting **illustrative diagnostic score is 30/100**. No firm-specific evidence was collected or assessed.

Users can change the hypothetical control statuses in the self-contained `index.html` to recalculate the score and explore weighted gaps. The accompanying `data.json` records the default scenario and model assumptions.

**Gap prioritisation:** For each control, the unearned weighted points equal `weight × (1 − status_factor)`. The largest weighted gap identifies the highest unearned contribution *under these assumed weights*; it does not establish legal materiality, assurance priority or a regulator's remediation ranking.

## Limitations and validation boundaries

The eight controls, their weights and the resulting score constitute an original, illustrative internal governance diagnostic. They are not prescribed ESRS-40a requirements, an official compliance assessment, an assurance opinion or a regulatory scoring methodology. All default control statuses are synthetic and do not represent evidence obtained from any undertaking. The cited ESRS-40a material was at consultation stage; applicability and final legal requirements must be assessed separately against the relevant adopted framework. No company-specific compliance conclusion is made.

## Management decision

Use the diagnostic to identify potential evidence gaps and prioritise entity-boundary documentation, data lineage and cross-report traceability. Confirm the applicable legal reporting framework and assurance requirements independently. Do not use the diagnostic score to assert ESRS compliance or audit readiness.

## Sources

- [EFRAG · ESRS-40a outreach · 29 Oct 2026](https://www.efrag.org/en/news-and-calendar/meetings-calendar/efrag-outreach-event-esrs40a-for-all-stakeholders)
- [ESMA · 2026 enforcement priorities · 13 Oct 2026](https://www.esma.europa.eu/press-news/esma-news/esma-sets-out-2026-european-common-enforcement-priorities)
