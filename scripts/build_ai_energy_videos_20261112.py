from pathlib import Path
import json,re
root=Path('site/daily-intelligence/2026-11-12');C=json.loads((root/'shared/studies.json').read_text())
bodies=[
'''Credit runs on power.
Subscribe for independent financial research; the full study is linked in the description.
The hypothesis is straightforward. A higher power bill reduces the cash available to service debt. But the mechanism depends on hedging, customer pricing and physical access to electricity.
We examined a continuous Oslo bankruptcy series covering two hundred and twenty-six months. A simple model using the previous month and calendar seasonality performed better than the same month a year earlier across a thirty-six-month holdout. Its average absolute error was about twelve bankruptcies, compared with roughly fifteen and a half for the seasonal benchmark.
That is useful context. It does not validate an electricity-driven default model.
The supplied electricity-price export contains only ten half-year observations. There is no matched panel of borrower energy bills, hedges and defaults. Estimating a causal credit elasticity from those inputs would promise more than the data support.
Instead, the dashboard makes the financing mechanism explicit. Change energy intensity, the unhedged share, pass-through and output losses. Then observe how the debt-service coverage proxy responds.
The forward scenario is conditional: if power costs rise while output falls, a borrower with thin margins and near-term principal repayments may face a disproportionate financing squeeze. A fixed-price contract can reduce price exposure while leaving connection risk unresolved.
This is research and scenario analysis, not a probability-of-default estimate or an investment recommendation.
The evidence that would change our view is a borrower-level panel showing whether energy exposure improves predictions beyond ordinary credit controls.
Which matters more in your underwriting: the price of electricity, or certainty of delivery?''',
'''Beware the foresight premium.
Subscribe for independent financial research; the full study is linked in the description.
Storage buys electricity now and sells it later. The investment question is whether an executable policy earns enough after losses, tariffs, degradation and capital costs.
We used forty-three thousand eight hundred zone-hour prices from a Norwegian power-market workbook. For each bidding zone, the first one hundred and eighty-one daily blocks selected a charging hour and a later selling hour. Those choices were frozen for the remaining one hundred and eighty-four blocks.
At ninety percent efficiency, the frozen schedule in the first Norwegian zone produced about one hundred and fifty-two kroner per daily one-megawatt-hour charge, before costs.
A strategy allowed to see the entire realised day produced a ceiling of about four hundred and seventy-six kroner. That gap is the value of information and optionality under this restricted model. It is not automatically available to an investor.
The experiment also exposes data limitations. The workbook uses sequential hour indices, and its final hour contains zero prices across all zones. We retained the observations and tested the final block separately.
The forward scenario is deliberately modest. Repeat the historical gross spread only as an assumption, then add availability, fees, degradation, cash-flow fade and discounting. The resulting value can change sharply.
NBIM’s November battery investment makes the topic timely, but Norwegian prices cannot value a North American storage platform.
This is a research experiment, not an investable return forecast.
The evidence that would strengthen the case is a feasible, cost-inclusive policy that survives several genuinely unseen years.
How much of a storage valuation survives when foresight is removed?''',
'''Profit is not replacement cash.
Subscribe for independent financial research; the full study is linked in the description.
Depreciation spreads an asset’s historical cost across an estimated useful life. It does not independently reveal how much cash is required to keep an AI service economically competitive.
We reconciled annual SEC data for six technology companies, preserving fiscal dates, filing accessions and accounting concepts. One technical detail matters: taxonomy tags change. Selecting an old capital-investment tag can accidentally turn a recent company history into an obsolete one.
The corrected data show why cash-flow reconciliation matters. Oracle’s fiscal year ending May twenty twenty-six records around thirty-two billion dollars of operating cash flow and nearly fifty-six billion of cash investment in property and equipment. The difference is negative before other investing and financing items.
That is not evidence of an accounting error. Total investment includes expansion, and cash investment can exclude lease additions. The study does not estimate maintenance capital spending or a company’s true economic asset life.
The scenario laboratory asks a narrower question. For a hypothetical asset cohort, what happens if the replacement horizon is shorter than the book allocation period? Change the horizon, residual value, tax assumption and compute share to inspect the arithmetic.
The forward risk is that competitive replacement needs absorb more cash than a valuation assumes. The opposite is also possible: older equipment may remain profitable in suitable workloads.
This is independent research, not an earnings restatement or an audit opinion.
Cohort-level utilisation, retirements and resale evidence would change the analysis.
When you value compute, which clock are you actually using?''',
'''Holdings can hide shared risks.
Subscribe for independent financial research; the full study is linked in the description.
The question is whether a globally diversified portfolio can still depend on a small number of economic outcomes: AI investment returns, semiconductor availability, regulation and reliable power.
We examined NBIM’s disclosed holdings at the end of June twenty twenty-six. The ten largest issuer names account for about twenty point nine percent of disclosed equity value.
A standard concentration measure gives the equivalent of roughly one hundred and fifty-four equally weighted positions. That is a statement about weights, not a count of independent return drivers.
We also matched a transparent six-company technology watchlist across equities and bonds. The exposures are displayed separately. Name matching is not complete legal-group consolidation.
A further control was essential. The real-estate and infrastructure files repeat country totals on multiple property or project rows. Summing every row would inflate portfolio values dramatically. We count each country total once.
The scenario laboratory then applies an explicit joint shock to selected equities, other equities and bonds. No probability is assigned, and correlation is not used to make simultaneous losses disappear.
The forward concern is common dependence on the same capital-spending cycle. But contracted infrastructure cash flows may behave differently from merchant technology earnings; the analysis keeps that distinction open.
NBIM’s November battery transaction is discussed as a later event, never inserted into the June snapshot.
This is research, not a replication of NBIM’s risk model or a portfolio recommendation.
Revenue-linked exposure and return data could overturn the common-factor hypothesis.
Does your diversification map follow sector labels, or the underlying cash flows?''',
'''Adoption is not productivity.
Subscribe for independent financial research; the full study is linked in the description.
In the supplied Eurostat data, almost twenty percent of EU enterprises with at least ten employees used AI in twenty twenty-five. That compares with just over eight percent in twenty twenty-three.
The size gap is substantial. Adoption reaches about seventeen percent among small enterprises, thirty percent among medium-sized firms and fifty-five percent among large firms.
But these percentages do not measure successful implementation or economic returns.
We compared lagged adoption with the following year’s real productivity growth per hour across twenty-seven EU countries. The estimated association was weak, and its robust confidence interval included zero.
We also imposed a genuine temporal test: fit the relationship using earlier adoption and growth, freeze the coefficients, then predict the next year. The result barely improved on a simple training-period average.
This does not prove that AI has no effect. The enterprise survey and national accounts cover different populations. Sector composition, investment, hours worked and measurement revisions can overwhelm a country-level signal.
The economic hypothesis remains that complementary investment and organisational redesign may delay gains. The competing hypothesis is that adoption counts overstate meaningful deployment.
Our forward scenario therefore separates addressable tasks, effective use, task-level improvement, leakage and implementation costs. These are assumptions, not estimated GDP multipliers.
Tangen’s discussion with Eric Schmidt frames Europe’s strategic question; it does not establish the causal answer.
This is independent research, not a forecast or policy ranking.
What would change our view is persistent firm-level improvement net of implementation costs.
What should count as adoption: access to a tool, or a measurable change in output?''',
'''Who captures the power dividend?
Subscribe for independent financial research; the full study is linked in the description.
AI demand may increase the value of power and flexibility. The fiscal question is who captures the incremental surplus after costs, investment and public support.
We assembled thirty years of Norwegian government accounts and thirty-six years of electricity balances. The fiscal history is consolidated: central and local government totals cannot simply be added without considering transfers.
The electricity balance for twenty twenty-five records roughly one hundred and sixty thousand gigawatt-hours of primary electricity production, eleven and a half thousand of imports and thirty-four thousand of exports.
These are measures of physical scale. They do not identify AI tax receipts or demonstrate spare capacity at a particular connection point.
The scenario laboratory follows an explicit waterfall. Additional demand creates producer revenue. An assumed operating margin determines profit. An effective tax captures part of that profit, while public ownership captures part of the remainder. Public subsidies and grid costs are then deducted.
This avoids counting the same pre-tax profit twice.
For perspective, a hypothetical one-hundred-megawatt load operating at ninety percent consumes around seven hundred and eighty-eight gigawatt-hours annually. Whether it creates a net public benefit depends on the counterfactual use of power and who pays for capacity.
The forward scenario can therefore produce a small dividend, a large one, or a fiscal cost. Aggregate historical dividends do not settle that question.
This is research and illustrative incidence analysis, not statutory tax guidance or a budget forecast.
Audited project-level taxes, distributions and public commitments would change the conclusion.
When we discuss an AI energy dividend, whose balance sheet are we measuring?'''
]
for c,body in zip(C,bodies):
 words=len(re.findall(r"\b[\w’'-]+\b",body));seconds=words/145*60
 assert 235<=words<=290,(c['kind'],words)
 text=f'# {c["title"]}\n\nProduction: English; British female avatar; vertical 9:16; talking head only; fixed camera; no charts or model overlays. Charts remain on the linked research page.\n\nNarration: {words} words. At 145 words/minute: {seconds:.0f} seconds. Target 1:40–2:00; actual recorded duration must be checked. First sentence is the two-second hook; immediate subscription CTA follows.\n\n'+body+'\n\nDescription link: https://mariianyaas.github.io/daily-intelligence/2026-11-12/'+c['slug']+'/\n'
 (root/c['slug']/'video-script.md').write_text(text)
 print(c['kind'],words,round(seconds))
