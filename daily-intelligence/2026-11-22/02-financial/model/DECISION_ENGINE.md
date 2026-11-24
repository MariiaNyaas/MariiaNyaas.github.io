# Deterministic decision engine — version 3.0.0

This engine translates **entered exposures, policies and scenarios into cash and portfolio consequences**. It does not predict exchange rates, estimate event probabilities, recommend trades or assert that a policy is optimal. The earlier EUR/NOK forecasting experiment remains a separate evidence layer; its lack of validated forecasting advantage is not changed by these calculations.

The engine is in [`../decision-engine.js`](../decision-engine.js), exposes `window.NVDecision` in a browser and `module.exports` in Node, and has no external dependencies. All functions are pure: they do not change their inputs, call services, write trades or persist client data.

## Units and input discipline

- Every spot and forward is **NOK per one unit of the specified currency**. NOK/NOK is identically 1.
- FX, local-asset and forecast-volume shocks are **arithmetic percentage changes**, not log returns. EUR/NOK +10% means one euro costs 10% more NOK.
- Money is in full currency units, not thousands or millions. Display formatting belongs in the interface.
- `hedgePct` and haircuts use percentages from 0 to 100. A hedge share of 50 means 50%, not 0.5%.
- Calendar dates use `YYYY-MM-DD`. Currency quote dates describe entered provenance; they do not make a quote executable or current.
- Required numeric blanks, nulls, booleans, NaN, infinities and non-decimal strings are rejected. **Missing information is not converted to zero.**
- An unhedged row may leave its unnecessary forward field blank. A missing optional stress-forward quote selects an explicitly labelled payoff proxy; it never becomes a zero forward.
- Deliberate optional scenario defaults are: zero FX shock for unspecified currencies, zero forecast-volume shock, zero local-asset shock for unspecified holdings, and an assumed 0% benchmark currency hedge. These are scenario conventions, not observations.
- An arithmetic FX shock must exceed −100%; asset and forecast-volume declines may equal −100%. Negative resulting exchange rates, numerical overflow and invalid calendar dates are rejected.

Every operation returns `{valid, errors, warnings, ...}`. Errors and warnings are arrays of `{path, code, message}`. On an invalid treasury, portfolio or collateral calculation, monetary totals are `null`; the UI must clear stale output and disable an export that would imply a valid result. A policy-comparison collection can have valid current policy but an invalid alternative lacking a forward quote: inspect every alternative's `valid` and the collection's `complete` flag.

## 1. Treasury cash-flow book

```javascript
NVDecision.treasury(rows, market, scenario = {}, options = {})
```

### Inputs

```javascript
const rows = [{
  id: 'payment-1', entity: 'Company A', currency: 'EUR',
  direction: 'payable',           // payable or receivable
  amount: 10000000,
  dueDate: '2027-01-31',
  certainty: 'committed',         // committed or forecast
  hedgePct: 50,
  forwardRate: 10.412,
  budgetRate: 10.312,
  nettingSet: '',                 // optional explicit settlement-netting set
  forwardSource: 'Illustrative assumption, not an executable quote'
}];
const market = {
  EUR: {spot: 10.312, asOf: '2026-10-30', source: 'Entered reference'}
};
const scenario = {
  fxShocks: {EUR: 10},
  volumePct: -20,
  valuationDate: '2026-11-24'      // optional; options.valuationDate is also accepted
};
```

The volume shock applies **only to forecast rows**. A committed payment does not disappear because the user reduces a sales forecast. The original hedge remains fixed when a forecast shrinks, grows, moves outside the entered assumption or is cancelled. Dates are not moved automatically.

### Arithmetic and reconciliation

Let `s = +1` for a payable and `−1` for a receivable; `A` be the original foreign amount, `A*` its scenario amount, `H = A × hedgePct/100` the fixed foreign hedge notional, `B` the budget rate, `S0` the reference spot, `S*` the scenario spot and `F` the entered contract forward.

```
Original budget cash = s × A × B
Volume effect        = s × (A* − A) × B
FX effect            = s × A* × (S* − B)
Hedge effect         = s × H × (F − S*)
Scenario cash        = s × [A* × S* + H × (F − S*)]
```

**Budget + volume + FX + hedge = scenario cash.** Positive cash means NOK paid; negative cash means NOK received. A positive change versus the signed budget is adverse for either direction: a larger payment or a smaller receipt.

`baselineCashNok` uses original volume, the current entered policy and `S0`. `changeVsCurrentBaselineNok` compares the scenario with that baseline. Supplementary `marketFxEffectNok` and `forwardPointsEffectNok` are diagnostic views and must not be added again to the waterfall.

If a forecast is cancelled, `A* = 0` while `H` remains fixed. The hedge payoff remains and can reverse the sign of net cash. The engine flags `overhedged_forecast` instead of silently reducing the contract. Its cash-equivalent treatment assumes residual currency is converted at the scenario spot; actual termination, delivery or resale must be arranged separately.

### Outputs

- `totals`: `budgetNok`, `baselineCashNok`, `scenarioCashNok`, the four decomposition fields, `changeVsBudgetNok`, `changeVsCurrentBaselineNok`, `grossOutflowsNok`, `grossInflowsNok`, `netCashNok` and authorized-netting aggregates.
- `rowResults`: normalized inputs, quote provenance, scenario amount, fixed hedge, overhedged amount, scenario spot, cash decomposition and residual local-currency exposure.
- `timeline`: one row per due date, chronological positive/negative cash equivalents and cumulative net cash. This is a schedule of entered settlement-date consequences, not a forecast of intraday funding peaks.
- `nettingGroups`: grouping is allowed **only** for the same explicitly entered entity, netting set, currency and due date. Without a set, every row remains separate. The same group name in different entities never permits netting.

The `gross*` amounts aggregate positive and negative **row cash equivalents**. They are not gross principal settlement legs. An aggregate net balance does not imply that cash may legally or operationally move across entities, borders, currencies or accounts.

## 2. Compare entered hedge policies

```javascript
NVDecision.comparePolicies(rows, market, scenario, options)
```

Returns the current policy and hypothetical 0%, 25%, 50%, 75% and 100% foreign-currency hedge policies, **all under the same scenario**. NOK-only rows remain unhedged. The benchmark is `current_policy`; it is not the statistical random-walk forecast.

An alternative normally uses the row's entered forward rate. An explicit `options.policyForwardRates` map keyed by row ID can supply a different rate for the hypothetical alternative. Existing contract rates remain unchanged in the current-policy reference. A nonzero hedge alternative without a forward quote is invalid; no spot rate is substituted as a free forward.

`deltaVsCurrentNok = alternative cash − current-policy cash`; `benefitVsCurrentNok` has the opposite sign. These are scenario cash differences, not expected savings or returns. Comparisons are hypothetical full-policy replacements. They do not assume existing contracts can be unwound for free, model transaction costs, establish an optimal hedge or authorise execution.

## 3. Reverse stress and policy feasibility

```javascript
NVDecision.reverseStress(row, market, {
  budgetLimitNok: 2000000, fxShockPct: 10, volumePct: 0
})
NVDecision.commonFxThreshold(rows, market, {
  budgetLimitNok: 2000000, volumePct: 0,
  shockMinPct: -99, shockMaxPct: 200
})
```

`budgetLimitNok` means the **maximum adverse increase in cash versus the original signed budget**, not a total-payment budget. The limit must be nonnegative.

For one row and a fixed scenario, the adverse cash change is linear in the hypothetical hedge share `h`:

```
adverse(h) = s × [A* × S* − A × B] + s × A × (F − S*) × h
```

The engine solves `adverse(h) ≤ limit` over the entire feasible domain `0 ≤ h ≤ 1`. It returns `lowerHedgePct` / `upperHedgePct` (also `minimumHedgePct` / `maximumHedgePct`). Depending on the entered forward and scenario, the admissible set can be a minimum hedge, a **maximum** hedge, every share, exactly 100%, or no feasible share. An impossible answer is not clipped into a fake feasible recommendation. The relation codes are `at_least`, `at_most`, `all`, `none`.

The book-level threshold applies the **same arithmetic percentage move to every foreign currency against NOK**. NOK itself remains unchanged. It reports the threshold, inequality direction, adverse NOK sensitivity per +1 percentage-point common move and the feasible interval within the displayed search range (default −99% to +200%). A mathematical boundary may lie outside that search range; it remains labelled separately. This is not the worst shock among all possible currency combinations and carries no probability.

### Independently specified worked example

For an illustrative €10m payable, `S0 = B = 10.312`, `S* = 11.3432` (+10%), `F = 10.412` (entered forward points +0.100), the terminal cash amounts are:

| Hedge | Cash paid, NOK | Adverse change versus NOK 103,120,000 budget |
|---:|---:|---:|
| 0% | 113,432,000 | 10,312,000 |
| 50% | 108,776,000 | 5,656,000 |
| 80% | 105,982,400 | 2,862,400 |
| 100% | 104,120,000 | 1,000,000 |

A NOK 2m maximum adverse change requires at least **89.261168%** in this one scenario and with these assumptions. This is a feasibility calculation, not a universal hedge recommendation. The forward is illustrative, not a sourced market quote.

## 4. Portfolio translation and fixed currency hedges

```javascript
NVDecision.portfolio(holdings, market, scenario, {benchmarkHedgePct: 0})
// holding: {id, label, assetClass, currency, valueLocal, hedgePct, forwardRate}
// scenario: {fxShocks:{USD:10}, assetShocks:{Equity:-20}, localReturns:{holding_id:-10}}
```

`localReturns` keyed by holding ID overrides the corresponding asset-class shock. `valueLocal` is the initial local-currency value; the currency hedge sells a fixed number of initial local-currency units equal to `valueLocal × hedgePct/100`.

For initial NOK value `V0`, local return `r` and arithmetic FX move `q`:

```
Local asset effect    = V0 × r
FX translation       = V0 × q
Interaction          = V0 × r × q
Currency hedge       = H × (F − S*)
Scenario value       = V0 + local + FX + interaction + hedge
```

A −20% asset move and +10% currency translation produce −12% unhedged NOK return, not −10%. A 100% hedge of initial currency units removes FX sensitivity only when local asset value is unchanged; asset gains/losses change the residual currency exposure. The engine flags a fixed hedge that exceeds the remaining local asset value.

The benchmark uses **identical holdings and identical local/FX shocks**, with the explicitly assumed benchmark currency-hedge share. Outputs include `benchmarkValueNok`, `activeVsBenchmarkNok` and `activeVsBenchmarkPct` (percentage points of initial total value). No actual NBIM holdings, mandate or official benchmark are implied. This is an assumed common end-horizon value and hedge payoff, not a current derivatives valuation. Zero initial portfolio value has no defined percentage return and returns `null` for that ratio.

## 5. Collateral and cash-liquidity stress

```javascript
NVDecision.collateral(positions, market, scenario, agreements)
```

Positions: `{id, entity, csaId, currency, direction:'buy'|'sell', notional, forwardRate, stressForwardRate?, discountFactor?, maturityDate?}`. A treasury payable's hedge buys foreign currency; a receivable's hedge sells it. `csaId` is distinct from a treasury cash-netting set.

Agreements: `{entity, csaId, thresholdNok, minimumTransferNok, postedCollateralNok, eligibleCollateralNok, haircutPct}`. **Every numeric agreement field is required and must be explicitly entered, including zero.** A CSA identifier alone does not establish zero thresholds, zero balances or zero haircut.

`postedCollateralNok` means collateral already posted **against this same calculated requirement and legally available to offset it**. Do not include segregated initial margin or an independent amount as though it automatically offsets variation margin. An initial-margin model is outside this engine.

### Valuation modes

- With an entered stressed remaining-tenor forward, the own-position mark is `directionSign × notional × (stressForwardRate − contractForward) × discountFactor`, where buy has sign +1 and sell −1.
- If a factor is absent, `scenario.discountRatePct`, `scenario.valuationDate` and the position's `maturityDate` can produce `exp(−rate × actualDays/365)`. A stated rate without the required dates is invalid. A mark with no supplied discount convention is explicitly labelled undiscounted (factor 1).
- Without a stressed remaining-tenor forward, the engine uses **only an undiscounted terminal-payoff proxy at the shocked spot**. It is not a live mark, an actual margin call or a forecast of a margin trajectory. A supplied discount factor is not falsely applied to turn this proxy into a live valuation.
- An entered maturity before the valuation date is rejected regardless of valuation mode.

### Grouping and incremental funding

Positions net only within the same explicit `entity + csaId`. Without a CSA identifier they remain separate. If the agreement is absent, requirements are `null`, `termsKnown` is false and adverse unassessed marks are shown separately. Known numerical totals are then **partial**, not an assertion of zero requirements elsewhere.

For known terms:

```
Required collateral = max(0, −net mark − threshold)
Incremental amount  = max(0, required collateral − already posted collateral)
Margin call         = incremental amount, if it meets the minimum transfer amount; else 0
Eligible collateral = separately allocated unencumbered amount × (1 − haircut)
Immediate cash need = max(0, margin call − eligible collateral)
```

Eligible collateral is a separately allocated pool for that agreement; the same security/cash cannot be counted in several pools. The interface must describe whether the selected agreement actually accepts those assets. Release from one CSA is displayed separately and never funds another group automatically. The engine does not model disputes, transfer delays, initial margin, changing haircuts, currency-conversion friction, concentration add-ons, intraday calls or regulatory applicability.

**Do not add the collateral call to terminal economic cash as another loss.** Collateral posting can cause a timing/funding need; it remains collateral and may be returned or used at settlement. A protected terminal payment can coexist with substantial intermediate liquidity demand.

## Verification and boundaries

Run from the research directory:

```bash
node model/scripts/test_decision_engine.cjs
```

The runner writes [`output/decision_validation.json`](output/decision_validation.json), including the exact engine SHA-256 and individual results. It checks independently specified monetary examples, both cash directions, cancellation with fixed hedge, multiple currencies, waterfall mass balances, authorized-netting isolation, policy benchmarks, forward-rate overrides, exact 100% and impossible feasibility boundaries, portfolio interaction, collateral terms/discounting/grouping, strict blank validation, numerical overflow and deterministic input preservation.

This is same-session implementation verification. It is not an external assurance opinion, an investment recommendation, legal confirmation of netting, hedge-accounting eligibility, or evidence that the historical forecast model can set dependable risk limits. Probabilities, CFaR, VaR and expected shortfall are intentionally not fabricated from the deterministic scenarios.
