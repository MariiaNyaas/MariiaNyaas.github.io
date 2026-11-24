'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const enginePath = path.resolve(__dirname, '../../decision-engine.js');
const E = require(enginePath);
const market = {
  EUR:{spot:10.312,asOf:'2026-10-30',source:'Frozen illustrative reference'},
  USD:{spot:10,asOf:'2026-10-30',source:'Illustrative assumption'},
  SEK:{spot:1,asOf:'2026-10-30',source:'Illustrative assumption'}
};
const flow = (changes={}) => ({id:'eur_pay',entity:'Company A',currency:'EUR',direction:'payable',amount:10000000,dueDate:'2027-01-31',certainty:'committed',hedgePct:50,forwardRate:10.412,budgetRate:10.312,nettingSet:'',forwardSource:'Illustrative assumption, not a market quote',...changes});
const holding = (changes={})=>({id:'holding',label:'Illustrative equities',assetClass:'Equity',currency:'USD',valueLocal:100,hedgePct:0,forwardRate:10,...changes});
const position = (changes={})=>({id:'hedge',entity:'Company A',csaId:'CSA-1',currency:'EUR',direction:'buy',notional:10000000,forwardRate:10.412,...changes});
const agreement=(changes={})=>({entity:'Company A',csaId:'CSA-1',thresholdNok:0,minimumTransferNok:0,postedCollateralNok:0,eligibleCollateralNok:0,haircutPct:0,...changes});
const close=(actual,expected,absoluteTolerance=1e-6)=>assert.ok(Number.isFinite(actual)&&Math.abs(actual-expected)<=Math.max(absoluteTolerance,Math.abs(expected)*2e-12),`${actual} != ${expected}`);
const valid=r=>assert.equal(r.valid,true,JSON.stringify(r.errors));
const tests=[];
function test(group,name,fn){try{fn();tests.push({group,name,status:'PASS'});}catch(error){tests.push({group,name,status:'FAIL',message:error.message});}}

test('cash_flow','Independent 10m EUR stress cases, all four hedge ratios',()=>{
  const expected=[[0,113432000,10312000],[50,108776000,5656000],[80,105982400,2862400],[100,104120000,1000000]];
  for(const [h,cash,delta]of expected){const r=E.treasury([flow({hedgePct:h})],market,{fxShocks:{EUR:10}});valid(r);close(r.totals.scenarioCashNok,cash);close(r.totals.changeVsBudgetNok,delta);}
});
test('cash_flow','Receivable cash sign and adverse NOK appreciation',()=>{
  const r=E.treasury([flow({direction:'receivable'})],market,{fxShocks:{EUR:-10}});valid(r);close(r.totals.scenarioCashNok,-98464000);close(r.totals.changeVsBudgetNok,4656000);close(r.totals.grossInflowsNok,98464000);close(r.totals.grossOutflowsNok,0);
});
test('cash_flow','Budget/volume/FX/hedge waterfall reconciles across two currencies',()=>{
  const r=E.treasury([flow({certainty:'forecast',budgetRate:10}),flow({id:'usd_in',currency:'USD',direction:'receivable',amount:1200000,hedgePct:75,forwardRate:10.1,budgetRate:9.8,certainty:'forecast'})],market,{fxShocks:{EUR:10,USD:-8},volumePct:-30});valid(r);
  for(const x of [...r.rowResults,r.totals])close(x.budgetNok+x.volumeEffectNok+x.fxEffectNok+x.hedgeEffectNok,x.scenarioCashNok);
  close(r.totals.scenarioCashNok,r.totals.grossOutflowsNok-r.totals.grossInflowsNok);
});
test('cash_flow','Committed volume is unchanged by forecast uncertainty',()=>{
  const a=E.treasury([flow()],market,{fxShocks:{EUR:10},volumePct:0});const b=E.treasury([flow()],market,{fxShocks:{EUR:10},volumePct:-100});valid(a);valid(b);close(a.totals.scenarioCashNok,b.totals.scenarioCashNok);close(b.rowResults[0].scenarioAmount,10000000);
});
test('cash_flow','Forecast cancellation leaves the original hedge alive',()=>{
  const r=E.treasury([flow({certainty:'forecast'})],market,{fxShocks:{EUR:10},volumePct:-100});valid(r);close(r.rowResults[0].hedgedAmount,5000000);close(r.rowResults[0].scenarioAmount,0);close(r.rowResults[0].overhedgedAmount,5000000);close(r.totals.scenarioCashNok,-4656000);assert.ok(r.warnings.some(w=>w.code==='overhedged_forecast'));
});
test('cash_flow','Forecast growth does not automatically scale the hedge',()=>{
  const r=E.treasury([flow({certainty:'forecast',hedgePct:80})],market,{fxShocks:{EUR:10},volumePct:25});valid(r);close(r.rowResults[0].scenarioAmount,12500000);close(r.rowResults[0].hedgedAmount,8000000);close(r.rowResults[0].residualExposureLocal,4500000);
});
test('cash_flow','Fully hedged fixed notional removes FX payoff sensitivity',()=>{
  const a=E.treasury([flow({hedgePct:100})],market,{fxShocks:{EUR:50}}),b=E.treasury([flow({hedgePct:100})],market,{fxShocks:{EUR:-50}});valid(a);valid(b);close(a.totals.scenarioCashNok,104120000);close(b.totals.scenarioCashNok,104120000);
});
test('cash_flow','Natural opposite flows remain gross without explicit matching consent',()=>{
  const r=E.treasury([flow({hedgePct:0}),flow({id:'receipt',direction:'receivable',hedgePct:0})],market,{});valid(r);close(r.totals.netCashNok,0);close(r.totals.authorizedNettingOutflowsNok,103120000);assert.equal(r.nettingGroups.length,2);
});
test('cash_flow','Netting requires the same entity, set, currency and due date',()=>{
  const a=flow({hedgePct:0,nettingSet:'Approved'}),b=flow({id:'receipt',direction:'receivable',hedgePct:0,nettingSet:'Approved'});
  const paired=E.treasury([a,b],market,{});valid(paired);assert.equal(paired.nettingGroups.length,1);close(paired.totals.authorizedNettingOutflowsNok,0);
  for(const replacement of [{entity:'Company B'},{dueDate:'2027-02-01'},{currency:'USD',budgetRate:10,forwardRate:10}]){const r=E.treasury([a,{...b,...replacement}],market,{});valid(r);assert.equal(r.nettingGroups.length,2);assert.ok(r.totals.authorizedNettingOutflowsNok>0);}
});
test('cash_flow','Timeline is chronologically sorted and reconciles to book total',()=>{
  const r=E.treasury([flow({dueDate:'2027-03-31'}),flow({id:'earlier',dueDate:'2027-01-31',direction:'receivable',amount:1000000})],market,{fxShocks:{EUR:10}});valid(r);assert.deepEqual(r.timeline.map(x=>x.dueDate),['2027-01-31','2027-03-31']);close(r.timeline.at(-1).cumulativeNetCashNok,r.totals.scenarioCashNok);
});

test('policies','Reference is current policy under the same scenario',()=>{
  const r=E.comparePolicies([flow({hedgePct:80})],market,{fxShocks:{EUR:10}});valid(r);assert.equal(r.benchmark,'current_policy');assert.equal(r.policies.length,6);close(r.policies[0].deltaVsCurrentNok,0);close(r.policies.find(p=>p.id==='h100').deltaVsCurrentNok,-1862400);close(r.policies.find(p=>p.id==='h0').deltaVsCurrentNok,7449600);
});
test('policies','New-policy rates can be supplied independently of current contracts',()=>{
  const r=E.comparePolicies([flow()],market,{fxShocks:{EUR:10}},{policyForwardRates:{eur_pay:10.5}});valid(r);close(r.current.totals.scenarioCashNok,108776000);close(r.policies.find(p=>p.id==='h100').totals.scenarioCashNok,105000000);
});
test('policies','Missing hedge quote prevents invented hedged alternatives',()=>{
  const r=E.comparePolicies([flow({hedgePct:0,forwardRate:''})],market,{fxShocks:{EUR:10}});valid(r);assert.equal(r.complete,false);assert.equal(r.policies.find(p=>p.id==='h0').valid,true);assert.equal(r.policies.find(p=>p.id==='h100').valid,false);
});
test('policies','NOK-only cash is not assigned a fictitious foreign currency hedge',()=>{
  const r=E.comparePolicies([flow({currency:'NOK',budgetRate:1,hedgePct:0,forwardRate:''})],market,{});valid(r);assert.equal(r.complete,true);for(const p of r.policies)close(p.totals.scenarioCashNok,10000000);
});

test('reverse_stress','Importer minimum ratio includes forward points',()=>{
  const r=E.reverseStress(flow(),market,{budgetLimitNok:2000000,fxShockPct:10});valid(r);assert.equal(r.feasible,true);close(r.minimumHedgePct,89.26116838487973);close(r.maximumHedgePct,100);assert.equal(r.currentPolicyWithinLimit,false);
});
test('reverse_stress','Exporter downside uses the correct sign',()=>{
  const r=E.reverseStress(flow({direction:'receivable'}),market,{budgetLimitNok:2000000,fxShockPct:-10});valid(r);close(r.minimumHedgePct,100*8312000/11312000);close(r.maximumHedgePct,100);
});
test('reverse_stress','Adverse entered forward can impose a maximum hedge ratio',()=>{
  const r=E.reverseStress(flow({forwardRate:11}),market,{budgetLimitNok:2000000,fxShockPct:0});valid(r);close(r.minimumHedgePct,0);close(r.maximumHedgePct,100*2000000/6880000);assert.equal(r.relation,'at_most');
});
test('reverse_stress','Exactly 100 percent endpoint is feasible',()=>{
  const r=E.reverseStress(flow(),market,{budgetLimitNok:1000000,fxShockPct:10});valid(r);assert.equal(r.feasible,true);close(r.minimumHedgePct,100);close(r.maximumHedgePct,100);
});
test('reverse_stress','Impossible limit is not clipped to a feasible answer',()=>{
  const r=E.reverseStress(flow(),market,{budgetLimitNok:500000,fxShockPct:10});valid(r);assert.equal(r.feasible,false);assert.equal(r.minimumHedgePct,null);assert.equal(r.maximumHedgePct,null);
});
test('reverse_stress','Hedge-independent scenario returns all feasible or none',()=>{
  const a=E.reverseStress(flow({forwardRate:11.3432}),market,{budgetLimitNok:11000000,fxShockPct:10}),b=E.reverseStress(flow({forwardRate:11.3432}),market,{budgetLimitNok:1000000,fxShockPct:10});valid(a);valid(b);assert.equal(a.relation,'all');assert.equal(a.feasible,true);assert.equal(b.relation,'none');assert.equal(b.feasible,false);
});
test('reverse_stress','Common-FX threshold reproduces the direct cash book boundary',()=>{
  const rows=[flow(),flow({id:'usd',currency:'USD',amount:2000000,budgetRate:10,forwardRate:10.1,hedgePct:25})];
  const t=E.commonFxThreshold(rows,market,{budgetLimitNok:4000000});valid(t);const r=E.treasury(rows,market,{fxShocks:{EUR:t.thresholdPct,USD:t.thresholdPct}});valid(r);close(r.totals.changeVsBudgetNok,4000000);assert.equal(t.relation,'at_most');
});
test('reverse_stress','Common shock gives exporter lower bound and fully hedged flat case',()=>{
  const r=E.commonFxThreshold([flow({direction:'receivable',hedgePct:0})],market,{budgetLimitNok:2000000});valid(r);assert.equal(r.relation,'at_least');close(r.thresholdPct,-100*2000000/103120000);
  const f=E.commonFxThreshold([flow({hedgePct:100})],market,{budgetLimitNok:2000000});valid(f);assert.equal(f.relation,'all');assert.equal(f.thresholdPct,null);
});

test('portfolio','Local and FX shocks include their interaction',()=>{
  const r=E.portfolio([holding()],market,{assetShocks:{Equity:-20},fxShocks:{USD:10}});valid(r);close(r.totals.initialValueNok,1000);close(r.totals.localAssetEffectNok,-200);close(r.totals.fxTranslationEffectNok,100);close(r.totals.interactionEffectNok,-20);close(r.totals.scenarioValueNok,880);close(r.totals.returnPct,-12);
});
test('portfolio','100 percent initial-unit hedge cancels FX only for unchanged local value',()=>{
  const r=E.portfolio([holding({hedgePct:100})],market,{fxShocks:{USD:10}});valid(r);close(r.totals.scenarioValueNok,1000);
  const loss=E.portfolio([holding({hedgePct:100})],market,{assetShocks:{Equity:-20},fxShocks:{USD:10}});valid(loss);close(loss.totals.scenarioValueNok,780);close(loss.rowResults[0].hedgedAmount,100);assert.ok(loss.warnings.some(x=>x.code==='hedge_exceeds_asset_value'));
});
test('portfolio','Same-holdings currency benchmark isolates policy difference',()=>{
  const r=E.portfolio([holding({hedgePct:50})],market,{assetShocks:{Equity:-20},fxShocks:{USD:10}},{benchmarkHedgePct:0});valid(r);close(r.totals.scenarioValueNok,830);close(r.totals.benchmarkValueNok,880);close(r.totals.activeVsBenchmarkNok,-50);assert.equal(r.benchmark.assumed,true);
});
test('portfolio','Portfolio waterfall reconciles across currencies and row overrides',()=>{
  const r=E.portfolio([holding(),holding({id:'bonds',label:'Bonds',assetClass:'Bonds',currency:'EUR',valueLocal:150,forwardRate:10.4,hedgePct:50})],market,{assetShocks:{Equity:-20,Bonds:-5},localReturns:{bonds:2},fxShocks:{EUR:-15,USD:10}});valid(r);const t=r.totals;close(t.initialValueNok+t.localAssetEffectNok+t.fxTranslationEffectNok+t.interactionEffectNok+t.hedgeEffectNok,t.scenarioValueNok);close(r.rowResults[1].localReturnPct,2);
});
test('portfolio','Unmapped imported asset class is disclosed as held constant',()=>{
  const r=E.portfolio([holding({assetClass:'Private asset'})],market,{assetShocks:{Equity:-20},fxShocks:{USD:10}});valid(r);close(r.rowResults[0].localReturnPct,0);assert.ok(r.warnings.some(w=>w.code==='asset_return_assumed_zero'));
});

test('collateral','Long EUR proxy loses on NOK appreciation and is labelled proxy',()=>{
  const r=E.collateral([position()],market,{fxShocks:{EUR:-10}},[agreement()]);valid(r);close(r.totals.netMarkNok,-11312000);close(r.totals.knownMarginCallNok,11312000);assert.equal(r.positions[0].valuationMode,'undiscounted_terminal_payoff_proxy');assert.equal(r.containsProxy,true);
});
test('collateral','Stressed forward and explicit discount factor determine the mark',()=>{
  const r=E.collateral([position({stressForwardRate:9.5,discountFactor:.95})],market,{fxShocks:{EUR:50}},[agreement()]);valid(r);close(r.totals.netMarkNok,-8664000);assert.equal(r.positions[0].valuationMode,'stress_forward_mark');assert.equal(r.containsProxy,false);
});
test('collateral','Continuous discount uses actual days over 365 and rejects expired positions',()=>{
  const r=E.collateral([position({stressForwardRate:9.5,maturityDate:'2027-01-01'})],market,{valuationDate:'2026-01-01',discountRatePct:5},[agreement()]);valid(r);close(r.positions[0].appliedDiscountFactor,Math.exp(-.05));
  assert.equal(E.collateral([position({stressForwardRate:9.5,maturityDate:'2025-01-01'})],market,{valuationDate:'2026-01-01'},[agreement()]).valid,false);
});
test('collateral','Threshold, posted collateral, haircut and minimum transfer reconcile',()=>{
  const r=E.collateral([position()],market,{fxShocks:{EUR:-10}},[agreement({thresholdNok:1000000,postedCollateralNok:2000000,eligibleCollateralNok:3000000,haircutPct:20})]);valid(r);close(r.groups[0].requiredCollateralNok,10312000);close(r.totals.knownMarginCallNok,8312000);close(r.totals.eligibleCollateralUsedNok,2400000);close(r.totals.immediateCashNeedNok,5912000);
  const m=E.collateral([position()],market,{fxShocks:{EUR:-10}},[agreement({minimumTransferNok:12000000})]);valid(m);close(m.totals.knownMarginCallNok,0);
});
test('collateral','Opposite positions net only inside the same entity and CSA',()=>{
  const p1=position(),p2=position({id:'opposite',direction:'sell'});
  const same=E.collateral([p1,p2],market,{fxShocks:{EUR:-10}},[agreement()]);valid(same);assert.equal(same.groups.length,1);close(same.totals.knownMarginCallNok,0);
  const split=E.collateral([p1,{...p2,entity:'Company B'}],market,{fxShocks:{EUR:-10}},[agreement(),agreement({entity:'Company B'})]);valid(split);assert.equal(split.groups.length,2);close(split.totals.knownMarginCallNok,11312000);
});
test('collateral','Missing CSA terms are unknown, not a zero-threshold margin assumption',()=>{
  const r=E.collateral([position({csaId:''}),position({id:'opposite',csaId:'',direction:'sell'})],market,{fxShocks:{EUR:-10}},[]);valid(r);assert.equal(r.groups.length,2);assert.equal(r.completeMarginTerms,false);assert.equal(r.groups[0].marginCallNok,null);close(r.totals.unassessedAdverseMarkNok,11312000);
});
test('collateral','Release in one CSA does not fund another CSA automatically',()=>{
  const r=E.collateral([position(),position({id:'opposite',entity:'Company B',direction:'sell'})],market,{fxShocks:{EUR:-10}},[agreement(),agreement({entity:'Company B',postedCollateralNok:5000000})]);valid(r);close(r.totals.immediateCashNeedNok,11312000);close(r.totals.potentialCollateralReleaseNok,5000000);
});

test('validation','Blank amount, hedge share and required forward are never zero',()=>{
  for(const field of ['amount','hedgePct','forwardRate','budgetRate'])for(const value of ['', ' ',null,false,Infinity,'0x10']){const r=E.treasury([flow({[field]:value})],market,{});assert.equal(r.valid,false,`${field}: ${value}`);assert.equal(r.totals,null);}
});
test('validation','Scenario blanks and invalid boundaries reject stale calculations',()=>{
  for(const scenario of [{volumePct:''},{fxShocks:{EUR:''}},{fxShocks:{EUR:-100}},{volumePct:-101},{fxShocks:{NOK:1}}])assert.equal(E.treasury([flow()],market,scenario).valid,false);
  assert.equal(E.treasury([flow({dueDate:'2026-02-30'})],market,{}).valid,false);
  assert.equal(E.treasury([flow(),flow()],market,{}).valid,false);
});
test('validation','Extreme numerical overflow returns no valid monetary result',()=>{
  const r=E.treasury([flow({amount:1e308})],market,{fxShocks:{EUR:1e308}});assert.equal(r.valid,false);assert.equal(r.totals,null);
});
test('validation','Invalid dates and blank collateral assumptions cannot become valid marks',()=>{
  assert.equal(E.collateral([position()],market,{},[agreement({thresholdNok:''})]).valid,false);
  assert.equal(E.collateral([position()],market,{},[{entity:'Company A',csaId:'CSA-1'}]).valid,false);
  assert.equal(E.collateral([position({stressForwardRate:9.5})],market,{discountRatePct:5},[agreement()]).valid,false);
  assert.equal(E.portfolio([holding({valueLocal:''})],market,{}).valid,false);
});
test('purity','Inputs remain unchanged and repeated results are deterministic',()=>{
  const rows=[flow({certainty:'forecast'})],s={fxShocks:{EUR:10},volumePct:-30},before=JSON.stringify({rows,market,s});
  const a=E.treasury(rows,market,s),b=E.treasury(rows,market,s);assert.deepEqual(a,b);assert.equal(JSON.stringify({rows,market,s}),before);
});

const groups=[...new Set(tests.map(t=>t.group))].map(group=>({group,passed:tests.filter(t=>t.group===group&&t.status==='PASS').length,failed:tests.filter(t=>t.group===group&&t.status==='FAIL').length}));
const failed=tests.filter(t=>t.status==='FAIL');
const report={title:'Deterministic decision-engine financial validation',engineVersion:E.version,generatedUtc:new Date().toISOString(),engineSha256:crypto.createHash('sha256').update(fs.readFileSync(enginePath)).digest('hex'),status:failed.length?'FAIL':'PASS',testCount:tests.length,passed:tests.length-failed.length,failed:failed.length,groups,tests,
  limits:['Same-session implementation verification, not external model validation.','Deterministic scenario arithmetic is tested; no probabilities, forecast superiority, live prices, legal netting enforceability or executable trading strategy are certified.','The historical prediction model has its own retained validation and remains separate.']};
const output=path.resolve(__dirname,'../output/decision_validation.json');fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,tests:tests.length,passed:report.passed,failed:report.failed,groups,failures:failed},null,2));
process.exitCode=failed.length?1:0;
