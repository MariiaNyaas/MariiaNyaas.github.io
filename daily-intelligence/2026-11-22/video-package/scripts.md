# Financial & Risk Intelligence — 22 November 2026

Production standard: Elodie Office 8 (`bc0ac3d5ed0345e3819416cd1d6d4656`), Renata — Clear & Professional (`6567750df960424fb6556202d7206640`), English US, vertical 9:16, no subtitles. The presenter is an AI narrator. Target runtime: 140 seconds without time-stretching or artificial silence.

## 01 — The Interest-Burden Threshold Test

Norway’s household credit stress is not rising in a straight line. It is clustering around a threshold.

This study asks a practical underwriting question: does a higher household interest burden improve the next-period forecast of bank loan losses, once we compare it with the simplest honest baseline?

We built a dated Norwegian panel from Statistics Norway and Norges Bank, aligned by observation period, publication date, unit, and revision status. The candidate model uses interest burden as the signal. The baseline simply carries the previous loss rate forward. Both are evaluated on a forward holdout, so tomorrow’s information never enters yesterday’s forecast.

The result is deliberately uncomfortable. The interest-burden model produced a mean absolute error of 0.573 percentage points. Persistence produced 0.475. In this sample, the more elaborate signal did not beat the naive benchmark, and the uncertainty interval around the incremental effect crosses zero.

That does not make the mechanism irrelevant. It changes the decision. Interest burden is better treated as a stress trigger and segmentation variable than as a stand-alone forecasting engine. The scenario laboratory therefore lets you vary rate pressure, income growth, and the loss-response coefficient, while keeping observed history separate from user-defined scenarios.

For a credit committee, the useful question is not whether one macro ratio predicts everything. It is where portfolio composition, refinancing dates, and borrower liquidity turn a broad rate shock into concentrated arrears.

The limitation is important: this is a latest-vintage holdout, not a vintage-perfect real-time backtest. Revisions and a short stress history constrain inference.

The practical takeaway is simple: retain interest burden in early-warning governance, but require segment-level validation before changing limits or provisions.

A stronger second-stage design would connect each household’s refinancing date, liquid savings, debt-service ratio, and actual arrears transition. That evidence could reveal whether the apparent threshold is an average masking a decisive tail. Until then, portfolio overlays should remain transparent, reversible, and monitored against realised outcomes.

The full research and interactive playground are available at the address in the description.

## 02 — Currency Risk & Treasury Decisions

The earlier financial-study script is withdrawn. The replacement research, published on 24 November 2026 at the same address, combines observed currency data, deterministic treasury and portfolio scenarios, budget boundaries, policy comparisons and collateral sensitivity. Hypothetical exposures are labelled separately from market observations. Historical forecast comparisons remain a supporting evidence layer and do not establish a validated trading signal.

Current study: https://mariianyaas.github.io/daily-intelligence/2026-11-22/02-financial/

## 03 — The Working-Capital Warning Test

The most visible accounting ratio was not the best warning signal in this sample.

This research tests whether a working-capital measure derived from SEC Company Facts improves the forecast of the next annual operating-margin change for a selected cross-company technology panel. Each filing fact is retained with its period, filing date, form, unit, and accession provenance. Duplicate facts are resolved by an explicit latest-filed rule, rather than silently averaged.

The candidate model produced a holdout mean absolute error of 5.415 percentage points. A simple persistence baseline produced 4.873. The proposed warning signal therefore underperformed the naive forecast.

That result is useful. Working capital can deteriorate for very different reasons: inventory build, customer mix, supplier terms, acquisition accounting, or rapid growth. Treating all movements as the same economic message creates false precision. The accounting mechanism remains plausible, but this specification does not earn the right to drive an audit conclusion.

The interactive laboratory lets you vary receivable days, inventory days, payable days, and revenue growth. It translates those assumptions into a cash-conversion effect, clearly labelled as a scenario rather than an observed fact. The historical charts remain tied to filed records.

For audit committees, the decision matrix is asymmetric. A sharp working-capital change should trigger document-level review and cash-flow reconciliation. It should not, by itself, be described as evidence of earnings manipulation or future margin collapse.

The limitations are material: the company panel is selective, accounting definitions differ, annual observations are sparse, and a latest-vintage holdout is not a filing-date real-time backtest.

What would change our mind? Consistent outperformance across issuers, sector-adjusted definitions, and stability after excluding acquisition years.

The practical takeaway is to use working capital as an audit question generator, then validate the mechanism in the notes and cash-flow statement.

The full research and interactive playground are available at the address in the description.

## 04 — The Voice-to-Capital Mismatch

Ownership is measured in capital. Stewardship influence is exercised through votes. They are not the same exposure.

Using NBIM’s published holdings and voting records, this study measures the absolute gap between portfolio ownership weight and recorded voting influence across 7,077 matched holdings. The value-weighted absolute mismatch is 0.093 percentage points. Four hundred and ten holdings show a gap of at least 0.10 percentage points, representing 12.89 percent of matched portfolio value.

These numbers do not prove governance failure. They reveal concentration in the translation from capital to voice. Differences can arise from share classes, securities lending, market-specific voting rules, record dates, or incomplete matching. The mechanism matters because the same nominal ownership stake can produce very different practical influence.

The dashboard separates observed matches from interpretation. You can filter the distribution and use the scenario laboratory to change ownership, eligible-vote coverage, and participation assumptions. The resulting influence estimate is explicitly a user scenario, not a reconstructed historical vote.

For boards and asset owners, the decision matrix focuses on exceptions. Large capital positions with persistent influence gaps deserve operational reconciliation. Small gaps in immaterial holdings do not warrant the same governance cost. The objective is not to maximize every vote mechanically; it is to know where the difference is intentional, structural, or simply unexplained.

The major limitation is denominator sensitivity. Holdings value, voting eligibility, and matched identifiers can change the measured gap. Automated reconciliation is not an external human review, and this study does not infer voting intent.

What would change our mind? A complete record-date denominator, verified share-class eligibility, and evidence that the mismatch disappears after those controls.

The practical takeaway is to govern stewardship as an exposure map: capital at risk, votes available, votes cast, and unresolved difference.

The full research and interactive playground are available at the address in the description.

## 05 — The Digital-Readiness Conversion Test

Europe does not have one AI adoption gap. It has a conversion gap between digital readiness and actual business use.

This study combines Eurostat indicators for ten European countries and asks whether digital intensity helps explain the level of enterprise AI adoption in 2025. The cross-sectional correlation is 0.937. In leave-one-country-out validation, the readiness model produced a mean absolute error of 2.462 percentage points, compared with 8.762 for a simple persistence-style country baseline.

That is a strong association and a useful validation result, but it is not a temporal backtest and it is not causal proof. With only ten countries, one institutional outlier can move the relationship materially. Digital intensity may also proxy for skills, management quality, firm size, sector composition, cloud access, or measurement practices.

The scenario laboratory lets you vary digital readiness, cloud use, and skills constraints to estimate an adoption range. These are transparent scenarios. They do not overwrite the official observations or imply that increasing one index mechanically creates AI deployment.

For economic policy, the mechanism is more specific than subsidizing technology purchases. Firms need complementary capabilities: clean data, process redesign, managerial accountability, cyber controls, and employees able to integrate the tools into production. Infrastructure without organizational conversion can leave adoption stalled.

The decision matrix distinguishes countries with low readiness from countries that look ready but under-convert. The first group needs foundations. The second needs implementation capability and sector-specific diffusion.

What would change our mind? A larger panel, repeated annual observations, stable out-of-sample performance, and results that survive controls for sector and firm size.

The practical takeaway is to measure the missing conversion step, not just broadband, cloud, or headline AI use in isolation.

The full research and interactive playground are available at the address in the description.

## 06 — The Sovereign Interest-Pass-Through Test

Higher rates do not hit Norway’s public finances through one line. They move income and expense at the same time.

Statistics Norway reports 2024 public-sector interest income of 254.54 billion Norwegian kroner and interest expense of 79.75 billion. The observed net position was therefore positive 174.79 billion kroner. But that aggregate does not mean every public entity benefits from tighter monetary conditions.

This study tests whether a simple policy-rate pass-through model improves the next-period forecast of net public interest income. It does not. The candidate specification underperforms the naive baseline, so we do not present the rate coefficient as a validated forecasting engine.

The economic mechanism is a balance-sheet duration problem. Asset yields can reprice quickly while long-dated debt costs move slowly, or the reverse. Central government, municipalities, public enterprises, and funds carry different assets, liabilities, currencies, and refinancing schedules. Aggregation can conceal the entity that actually bears the squeeze.

The playground therefore lets you change the share of floating-rate assets, floating-rate debt, reinvestment speed, and the policy-rate shock. The output is a scenario decomposition, clearly separated from the historical accounts.

For public-finance committees, the practical decision is to monitor repricing ladders and distribution, not only the consolidated net number. A positive national position can coexist with acute municipal budget pressure.

The limitations are explicit: the sample is short, institutional composition changes, and latest-vintage accounts do not reproduce the information set available at each historical budget date.

What would change our mind? Entity-level duration data, vintage budget forecasts, and stable predictive improvement over a no-change baseline.

The takeaway is straightforward: treat rate exposure as a map of who reprices, when, and against which revenue base.

The full research and interactive playground are available at the address in the description.

## 07 — The Museum Subsidy Resilience Test

Museum attendance can recover while the funding model becomes more fragile.

Using official Norwegian museum statistics, this study records 11.527 million visits, 5.573 billion Norwegian kroner in public contributions, a 71.13 percent subsidy share, and approximately 196 kroner of own revenue per visit in the latest observed year.

The research question is not whether subsidy is good or bad. It is whether attendance, earned income, and public support absorb shocks in the same way. They do not. Visitor growth can improve ticket and retail revenue, but collections care, conservation, security, and buildings contain large fixed costs. A museum can look culturally successful and remain financially exposed.

We test a simple resilience model against a naive baseline. The candidate does not show superior predictive performance, so the study does not convert the relationship into a forecast claim. Instead, the dashboard uses observed history to anchor a transparent scenario laboratory.

You can vary visitor volume, own revenue per visit, public support, and fixed-cost inflation. The output shows the implied funding gap and break-even pressure. Those figures are scenarios, not fabricated observations.

For boards and public funders, the decision matrix separates temporary demand weakness from structural funding risk. A short visitor shock may justify liquidity support. Persistent cost growth with flat earned income requires a different response: pricing, programming, endowment policy, or a renegotiated public mandate.

The limitation is comparability. Museum scope, consolidation, accounting practice, and pandemic effects can change across years. Automated checks are not an external curatorial or audit review.

What would change our mind? Institution-level panels, consistent cost classifications, and evidence that the model beats a simple baseline across funding regimes.

The practical takeaway is to evaluate cultural return and financial resilience together, without pretending they are the same variable.

The full research and interactive playground are available at the address in the description.
