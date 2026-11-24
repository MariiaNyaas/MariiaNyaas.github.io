/* Nord Veritas deterministic decision arithmetic, v3.0.0.
 * All spot/forward quotes are NOK per unit of foreign currency.
 * This module makes no probabilistic, live-price or execution claim. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.NVDecision = api;
})(typeof window !== 'undefined' ? window : typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const VERSION = '3.0.0';
  const DAY_MS = 86400000;
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
  const object = o => o !== null && typeof o === 'object' && !Array.isArray(o);
  const absent = v => v === undefined || v === null || (typeof v === 'string' && v.trim() === '');
  const issue = (list, path, code, message) => list.push({path, code, message});
  const uniqueIssues = a => [...new Map(a.map(x => [`${x.path}|${x.code}|${x.message}`, x])).values()];
  function numeric(v, path, errors, settings) {
    const s = settings || {};
    if (v === undefined && own(s, 'defaultValue')) return s.defaultValue;
    if (typeof v !== 'number' && typeof v !== 'string') {
      issue(errors, path, 'number_required', 'Enter a finite number; blanks, nulls and booleans are not zero.');
      return NaN;
    }
    if (typeof v === 'string' && !/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(v.trim())) {
      issue(errors, path, 'number_required', 'Enter a finite decimal number; an empty field is not zero.');
      return NaN;
    }
    const n = Number(v);
    if (!Number.isFinite(n)) issue(errors, path, 'number_required', 'Enter a finite number.');
    else if (s.min !== undefined && n < s.min) issue(errors, path, 'below_minimum', `Value must be at least ${s.min}.`);
    else if (s.max !== undefined && n > s.max) issue(errors, path, 'above_maximum', `Value must be at most ${s.max}.`);
    else if (s.positive && n <= 0) issue(errors, path, 'positive_required', 'Value must be greater than zero.');
    return n;
  }
  function string(v, path, errors, required) {
    if (v === undefined || v === null) {
      if (required) issue(errors, path, 'text_required', 'Enter a non-empty text value.');
      return '';
    }
    if (typeof v !== 'string') { issue(errors, path, 'text_required', 'Text is required.'); return ''; }
    const value = v.trim();
    if (required && !value) issue(errors, path, 'text_required', 'Enter a non-empty text value.');
    return value;
  }
  function currency(v, path, errors) {
    const c = string(v, path, errors, true).toUpperCase();
    if (c && !/^[A-Z]{3}$/.test(c)) issue(errors, path, 'currency_code', 'Use a three-letter currency code.');
    return c;
  }
  function date(v, path, errors, required) {
    if (!required && v === undefined) return null;
    if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v) || !Number.isFinite(Date.parse(v + 'T00:00:00Z'))) {
      issue(errors, path, 'date_required', 'Use a valid calendar date in YYYY-MM-DD format.'); return null;
    }
    if (new Date(v + 'T00:00:00Z').toISOString().slice(0, 10) !== v) {
      issue(errors, path, 'date_required', 'This calendar date does not exist.'); return null;
    }
    return v;
  }
  function baseResult(errors, warnings) { return {version:VERSION, valid:errors.length === 0, errors:uniqueIssues(errors), warnings:uniqueIssues(warnings)}; }
  function checkArray(rows, label, errors, allowEmpty) {
    if (!Array.isArray(rows) || (!allowEmpty && rows.length === 0)) {
      issue(errors, label, 'rows_required', allowEmpty ? 'Supply an array.' : 'Supply at least one row.'); return [];
    }
    return rows;
  }
  function checkIds(rows, errors, label) {
    const seen = new Set();
    rows.forEach((r, i) => { if (seen.has(r.id)) issue(errors, `${label}[${i}].id`, 'duplicate_id', 'Every row needs a unique ID.'); seen.add(r.id); });
  }
  function readMarket(market, c, errors, warnings) {
    const path = `market.${c}`;
    if (c === 'NOK' && (!object(market) || !own(market, c))) return {spot:1, asOf:null, source:'NOK identity'};
    const q = object(market) && object(market[c]) ? market[c] : null;
    if (!q) { issue(errors, path, 'market_quote_required', `Enter the NOK price of one ${c}.`); return {spot:NaN, asOf:null, source:''}; }
    const spot = numeric(q.spot, `${path}.spot`, errors, {positive:true});
    if (c === 'NOK' && spot !== 1) issue(errors, `${path}.spot`, 'nok_identity', 'NOK/NOK must equal 1.');
    let asOf = null;
    if (absent(q.asOf)) issue(warnings, `${path}.asOf`, 'quote_date_unknown', 'Quote date is not supplied; this is not a verified current market price.');
    else asOf = date(q.asOf, `${path}.asOf`, errors, true);
    const source = typeof q.source === 'string' ? q.source.trim() : '';
    if (c !== 'NOK' && !source) issue(warnings, `${path}.source`, 'quote_source_unknown', 'Quote source is not supplied.');
    return {spot, asOf, source};
  }
  function readScenario(input, errors, options) {
    const s = input === undefined ? {} : input;
    if (!object(s)) { issue(errors, 'scenario', 'object_required', 'Scenario must be an object.'); return {fxShocks:{}, volumePct:NaN}; }
    const fxShocks = {};
    if (s.fxShocks !== undefined && !object(s.fxShocks)) issue(errors, 'scenario.fxShocks', 'object_required', 'FX shocks must be an object keyed by currency.');
    Object.entries(object(s.fxShocks) ? s.fxShocks : {}).forEach(([key, value]) => {
      const c = currency(key, `scenario.fxShocks.${key}`, errors);
      const n = numeric(value, `scenario.fxShocks.${key}`, errors);
      if (n <= -100) issue(errors, `scenario.fxShocks.${key}`, 'nonpositive_spot', 'An arithmetic FX shock must be greater than -100%.');
      if (c === 'NOK' && n !== 0) issue(errors, `scenario.fxShocks.${key}`, 'nok_identity', 'NOK cannot be shocked against itself.');
      fxShocks[c] = n;
    });
    const volumePct = numeric(s.volumePct, 'scenario.volumePct', errors, {defaultValue:0, min:-100});
    const vd = s.valuationDate !== undefined ? s.valuationDate : options && options.valuationDate;
    const valuationDate = vd === undefined ? null : date(vd, 'scenario.valuationDate', errors, true);
    return {...s, fxShocks, volumePct, valuationDate};
  }
  function forward(value, hedgePct, path, errors) {
    if (hedgePct === 0 && absent(value)) return null;
    return numeric(value, path, errors, {positive:true});
  }
  function cashRow(raw, i, market, scenario, errors, warnings) {
    const path = `rows[${i}]`, r = object(raw) ? raw : {};
    if (!object(raw)) issue(errors, path, 'object_required', 'A row must be an object.');
    const id = string(r.id, `${path}.id`, errors, true);
    const entity = string(r.entity, `${path}.entity`, errors, true);
    const c = currency(r.currency, `${path}.currency`, errors);
    const direction = r.direction;
    if (!['payable','receivable'].includes(direction)) issue(errors, `${path}.direction`, 'direction_required', 'Choose payable or receivable.');
    const certainty = r.certainty;
    if (!['committed','forecast'].includes(certainty)) issue(errors, `${path}.certainty`, 'certainty_required', 'Choose committed or forecast.');
    const amount = numeric(r.amount, `${path}.amount`, errors, {min:0});
    const hedgePct = numeric(r.hedgePct, `${path}.hedgePct`, errors, {min:0,max:100});
    const forwardRate = forward(r.forwardRate, hedgePct, `${path}.forwardRate`, errors);
    const budgetRate = numeric(r.budgetRate, `${path}.budgetRate`, errors, {positive:true});
    const dueDate = date(r.dueDate, `${path}.dueDate`, errors, true);
    const nettingSet = string(r.nettingSet, `${path}.nettingSet`, errors, false);
    const forwardSource = string(r.forwardSource, `${path}.forwardSource`, errors, false);
    const quote = readMarket(market, c, errors, warnings);
    if (hedgePct > 0 && !forwardSource) issue(warnings, `${path}.forwardSource`, 'forward_source_unknown', 'Forward rate is an entered assumption without a source.');
    if (scenario.valuationDate && dueDate && dueDate < scenario.valuationDate) issue(warnings, `${path}.dueDate`, 'past_due_date', 'This cash-flow date precedes the valuation date.');
    if (c === 'NOK' && (budgetRate !== 1 || (forwardRate !== null && forwardRate !== 1))) issue(errors, path, 'nok_identity', 'NOK budget and forward rates must equal 1.');
    return {id,entity,currency:c,direction,certainty,amount,hedgePct,forwardRate,budgetRate,dueDate,nettingSet,forwardSource,...quote};
  }
  function finiteOutput(result, errors) {
    const visit = (value, path) => {
      if (typeof value === 'number' && !Number.isFinite(value)) issue(errors, path, 'numerical_range', 'The calculation exceeds the finite numerical range; reduce extreme inputs.');
      else if (Array.isArray(value)) value.forEach((v,i) => visit(v, `${path}[${i}]`));
      else if (object(value)) Object.entries(value).forEach(([k,v]) => visit(v, `${path}.${k}`));
    };
    visit(result, 'result');
  }
  function treasury(rows, market, scenario, options) {
    const errors = [], warnings = [], s = readScenario(scenario, errors, options);
    const parsed = checkArray(rows, 'rows', errors).map((r,i) => cashRow(r,i,market,s,errors,warnings));
    checkIds(parsed, errors, 'rows');
    if (errors.length) return {...baseResult(errors,warnings),totals:null,rowResults:[],timeline:[],nettingGroups:[]};
    const rowResults = parsed.map((r,i) => {
      const sign = r.direction === 'payable' ? 1 : -1;
      const scenarioAmount = r.amount * (r.certainty === 'forecast' ? 1+s.volumePct/100 : 1);
      const hedgedAmount = r.amount*r.hedgePct/100;
      const overhedgedAmount = Math.max(0,hedgedAmount-scenarioAmount);
      const fxShockPct = s.fxShocks[r.currency] === undefined ? 0 : s.fxShocks[r.currency];
      const scenarioSpot = r.spot*(1+fxShockPct/100);
      if (!(scenarioSpot > 0)) issue(errors, `rows[${i}].scenarioSpot`, 'numerical_range', 'The implied exchange rate must remain positive within numerical precision.');
      const F = r.forwardRate === null ? r.spot : r.forwardRate;
      const budgetNok = sign*r.amount*r.budgetRate;
      const baselineCashNok = sign*(r.amount*r.spot+hedgedAmount*(F-r.spot));
      const volumeEffectNok = sign*(scenarioAmount-r.amount)*r.budgetRate;
      const fxEffectNok = sign*scenarioAmount*(scenarioSpot-r.budgetRate);
      const hedgeEffectNok = sign*hedgedAmount*(F-scenarioSpot);
      const scenarioCashNok = sign*(scenarioAmount*scenarioSpot+hedgedAmount*(F-scenarioSpot));
      if (overhedgedAmount > Math.max(1,r.amount)*1e-12) issue(warnings, `rows[${i}]`, 'overhedged_forecast', 'The original fixed hedge exceeds the remaining forecast exposure. It is not automatically cancelled or resized.');
      return {...r,originalAmount:r.amount,scenarioAmount,hedgedAmount,overhedgedAmount,fxShockPct,scenarioSpot,budgetNok,baselineCashNok,scenarioCashNok,volumeEffectNok,fxEffectNok,hedgeEffectNok,
        marketFxEffectNok:sign*(scenarioAmount-hedgedAmount)*(scenarioSpot-r.spot),
        forwardPointsEffectNok:sign*hedgedAmount*(F-r.spot),
        changeVsBudgetNok:scenarioCashNok-budgetNok,changeVsCurrentBaselineNok:scenarioCashNok-baselineCashNok,
        residualExposureLocal:scenarioAmount-hedgedAmount};
    });
    const fields=['budgetNok','baselineCashNok','scenarioCashNok','volumeEffectNok','fxEffectNok','hedgeEffectNok','marketFxEffectNok','forwardPointsEffectNok','changeVsBudgetNok','changeVsCurrentBaselineNok'];
    const totals = Object.fromEntries(fields.map(k=>[k,rowResults.reduce((a,r)=>a+r[k],0)]));
    totals.grossOutflowsNok=rowResults.reduce((a,r)=>a+Math.max(0,r.scenarioCashNok),0);
    totals.grossInflowsNok=rowResults.reduce((a,r)=>a+Math.max(0,-r.scenarioCashNok),0);
    totals.netCashNok=totals.scenarioCashNok;
    const dates=new Map(), groups=new Map();
    rowResults.forEach(r=>{
      if(!dates.has(r.dueDate))dates.set(r.dueDate,{dueDate:r.dueDate,outflowsNok:0,inflowsNok:0,netCashNok:0,rowIds:[]});
      const t=dates.get(r.dueDate);t.outflowsNok+=Math.max(0,r.scenarioCashNok);t.inflowsNok+=Math.max(0,-r.scenarioCashNok);t.netCashNok+=r.scenarioCashNok;t.rowIds.push(r.id);
      const key=JSON.stringify(r.nettingSet?[r.entity,r.nettingSet,r.currency,r.dueDate]:[r.entity,'unnetted',r.id]);
      if(!groups.has(key))groups.set(key,{key,entity:r.entity,nettingSet:r.nettingSet,currency:r.currency,dueDate:r.dueDate,explicitNetting:!!r.nettingSet,rowIds:[],netCashNok:0,grossOutflowsNok:0,grossInflowsNok:0});
      const g=groups.get(key);g.rowIds.push(r.id);g.netCashNok+=r.scenarioCashNok;g.grossOutflowsNok+=Math.max(0,r.scenarioCashNok);g.grossInflowsNok+=Math.max(0,-r.scenarioCashNok);
    });
    const timeline=[...dates.values()].sort((a,b)=>a.dueDate.localeCompare(b.dueDate));
    let cumulative=0;timeline.forEach(t=>{cumulative+=t.netCashNok;t.cumulativeNetCashNok=cumulative;});
    const nettingGroups=[...groups.values()].map(g=>({...g,settlementOutflowNok:g.explicitNetting?Math.max(0,g.netCashNok):g.grossOutflowsNok,settlementInflowNok:g.explicitNetting?Math.max(0,-g.netCashNok):g.grossInflowsNok}));
    totals.authorizedNettingOutflowsNok=nettingGroups.reduce((a,g)=>a+g.settlementOutflowNok,0);
    totals.authorizedNettingInflowsNok=nettingGroups.reduce((a,g)=>a+g.settlementInflowNok,0);
    const out={totals,rowResults,timeline,nettingGroups};finiteOutput(out,errors);
    if(errors.length)return{...baseResult(errors,warnings),totals:null,rowResults:[],timeline:[],nettingGroups:[]};
    return {...baseResult(errors,warnings),...out,signConvention:'Positive = NOK paid; negative = NOK received.',scenario:s,
      nettingAssumption:'Only an explicit entity + nettingSet + currency + same due date permits the displayed settlement netting. Book totals and dates are arithmetic aggregates, not permission to transfer cash across entities.',
      cashConvention:'End-date NOK cash equivalents assume any residual foreign currency is converted at the entered scenario spot. Gross fields aggregate positive and negative row equivalents; they are not gross principal settlement legs or a peak intraday funding forecast.',
      decomposition:'budget + volume effect + FX effect + hedge effect = scenario cash; supplementary market-FX/forward-point fields must not be added again.'};
  }
  function comparePolicies(rows, market, scenario, options) {
    const current=treasury(rows,market,scenario,options);
    if(!current.valid)return{...baseResult(current.errors,current.warnings),current,policies:[],benchmark:'current_policy'};
    const policyRates=options&&object(options.policyForwardRates)?options.policyForwardRates:{};
    const specs=[{id:'current',label:'Current policy',hedgePct:null},...[0,25,50,75,100].map(h=>({id:`h${h}`,label:`${h}% hedge`,hedgePct:h}))];
    const policies=specs.map(p=>{
      const alternative=p.hedgePct===null?rows:rows.map(r=>({...r,hedgePct:String(r.currency).trim().toUpperCase()==='NOK'?0:p.hedgePct,forwardRate:own(policyRates,r.id)?policyRates[r.id]:r.forwardRate}));
      const result=p.hedgePct===null?current:treasury(alternative,market,scenario,options);
      return{...p,valid:result.valid,errors:result.errors,warnings:result.warnings,totals:result.totals,
        deltaVsCurrentNok:result.valid?result.totals.scenarioCashNok-current.totals.scenarioCashNok:null,
        benefitVsCurrentNok:result.valid?current.totals.scenarioCashNok-result.totals.scenarioCashNok:null};
    });
    const warnings=[...current.warnings];
    issue(warnings,'policies','hypothetical_policy_rates','Alternative policies use the entered forward rate (or an explicit per-row policyForwardRates override). Existing contracts are not assumed freely cancellable; unwind costs, execution, fees and collateral are outside this terminal comparison.');
    return{...baseResult([],warnings),current,policies,benchmark:'current_policy',complete:policies.every(p=>p.valid)};
  }
  function solveLinearUpper(intercept,slope,limit,min,max) {
    const tolerance=16*Number.EPSILON*Math.max(1,Math.abs(intercept),Math.abs(limit));
    if(slope===0)return{feasible:intercept<=limit+tolerance,lower:intercept<=limit+tolerance?min:null,upper:intercept<=limit+tolerance?max:null,boundary:null,relation:intercept<=limit+tolerance?'all':'none'};
    const boundary=(limit-intercept)/slope;
    const lower=slope<0?Math.max(min,boundary):min,upper=slope>0?Math.min(max,boundary):max;
    const feasible=lower<=upper+1e-12;
    return{feasible,lower:feasible?Math.max(min,Math.min(max,lower)):null,upper:feasible?Math.max(min,Math.min(max,upper)):null,boundary,relation:slope<0?'at_least':'at_most'};
  }
  function reverseStress(row,market,parameters) {
    const p=object(parameters)?parameters:{},errors=[],warnings=[];
    const limit=numeric(p.budgetLimitNok,'parameters.budgetLimitNok',errors,{min:0});
    const fxShockPct=numeric(p.fxShockPct,'parameters.fxShockPct',errors);
    const volumePct=numeric(p.volumePct,'parameters.volumePct',errors,{defaultValue:0,min:-100});
    const c=object(row)&&typeof row.currency==='string'?row.currency.trim().toUpperCase():'';
    const base=treasury([row],market,{fxShocks:{[c]:fxShockPct},volumePct});
    errors.push(...base.errors);warnings.push(...base.warnings);
    const F=numeric(object(row)?row.forwardRate:undefined,'rows[0].forwardRate',errors,{positive:true});
    if(errors.length)return{...baseResult(errors,warnings),feasible:false,lowerHedgePct:null,upperHedgePct:null};
    const r=base.rowResults[0],sign=r.direction==='payable'?1:-1;
    const cash0=sign*r.scenarioAmount*r.scenarioSpot;
    const slope=sign*r.originalAmount*(F-r.scenarioSpot);
    const intercept=cash0-r.budgetNok,solution=solveLinearUpper(intercept,slope,limit,0,1);
    const out={feasible:solution.feasible,lowerHedgePct:solution.lower===null?null:solution.lower*100,upperHedgePct:solution.upper===null?null:solution.upper*100,
      minimumHedgePct:solution.lower===null?null:solution.lower*100,maximumHedgePct:solution.upper===null?null:solution.upper*100,
      currentHedgePct:r.hedgePct,currentPolicyWithinLimit:r.changeVsBudgetNok<=limit+1e-8,limitNok:limit,
      cashAtZeroNok:cash0,cashAtFullNok:cash0+slope,adverseAtZeroNok:intercept,adverseAtFullNok:intercept+slope,
      currentScenarioCashNok:r.scenarioCashNok,currentAdverseNok:r.changeVsBudgetNok,relation:solution.relation,
      boundaryHedgePct:solution.boundary===null?null:solution.boundary*100,budgetNok:r.budgetNok,fxShockPct,volumePct};
    finiteOutput(out,errors);return{...baseResult(errors,warnings),...out,
      interpretation:'Feasible hedge interval for this one entered scenario and maximum adverse cash change versus the original budget; not an optimal hedge recommendation.'};
  }
  function commonFxThreshold(rows,market,parameters) {
    const p=object(parameters)?parameters:{},errors=[],warnings=[];
    const limit=numeric(p.budgetLimitNok,'parameters.budgetLimitNok',errors,{min:0});
    const volumePct=numeric(p.volumePct,'parameters.volumePct',errors,{defaultValue:0,min:-100});
    const min=numeric(p.shockMinPct,'parameters.shockMinPct',errors,{defaultValue:-99});
    const max=numeric(p.shockMaxPct,'parameters.shockMaxPct',errors,{defaultValue:200});
    if(min<=-100)issue(errors,'parameters.shockMinPct','nonpositive_spot','Minimum FX shock must exceed -100%.');
    if(max<min)issue(errors,'parameters.shockMaxPct','invalid_range','Maximum shock must not be below minimum shock.');
    const base=treasury(rows,market,{volumePct});errors.push(...base.errors);warnings.push(...base.warnings);
    if(errors.length)return{...baseResult(errors,warnings),feasible:false,lowerShockPct:null,upperShockPct:null};
    const intercept=base.totals.changeVsBudgetNok;
    const perPct=base.rowResults.reduce((a,r)=>a+(r.currency==='NOK'?0:(r.direction==='payable'?1:-1)*(r.scenarioAmount-r.hedgedAmount)*r.spot/100),0);
    const sol=solveLinearUpper(intercept,perPct,limit,min,max);
    const out={feasible:sol.feasible,lowerShockPct:sol.lower,upperShockPct:sol.upper,boundaryShockPct:sol.boundary,thresholdPct:sol.boundary,relation:sol.relation,
      adversePer1PctNok:perPct,adverseAtZeroNok:intercept,limitNok:limit,volumePct,testedRange:{minPct:min,maxPct:max},currencies:[...new Set(base.rowResults.filter(r=>r.currency!=='NOK').map(r=>r.currency))]};
    finiteOutput(out,errors);return{...baseResult(errors,warnings),...out,
      interpretation:'A common arithmetic percentage move in every foreign currency against NOK, holding entered forwards and hedge notionals fixed. This is not a worst-case multidimensional shock or a probability.'};
  }
  function portfolio(rows,market,scenario,options) {
    const errors=[],warnings=[],s=readScenario(scenario,errors,options),o=object(options)?options:{};
    const benchmarkHedgePct=numeric(o.benchmarkHedgePct,'options.benchmarkHedgePct',errors,{defaultValue:0,min:0,max:100});
    for(const key of ['assetShocks','localReturns'])if(s[key]!==undefined&&!object(s[key]))issue(errors,`scenario.${key}`,'object_required',`${key} must be an object.`);
    const parsed=checkArray(rows,'rows',errors).map((raw,i)=>{
      const r=object(raw)?raw:{},path=`rows[${i}]`;
      if(!object(raw))issue(errors,path,'object_required','A holding must be an object.');
      const id=string(r.id,`${path}.id`,errors,true),label=string(r.label,`${path}.label`,errors,true),assetClass=string(r.assetClass,`${path}.assetClass`,errors,true),c=currency(r.currency,`${path}.currency`,errors);
      const valueLocal=numeric(r.valueLocal,`${path}.valueLocal`,errors,{min:0}),hedgePct=numeric(r.hedgePct,`${path}.hedgePct`,errors,{min:0,max:100});
      const forwardRate=c==='NOK'&&absent(r.forwardRate)?1:forward(r.forwardRate,Math.max(hedgePct,benchmarkHedgePct),`${path}.forwardRate`,errors),quote=readMarket(market,c,errors,warnings);
      const hasRowReturn=object(s.localReturns)&&own(s.localReturns,id),hasClassReturn=object(s.assetShocks)&&own(s.assetShocks,assetClass);
      const rawReturn=hasRowReturn?s.localReturns[id]:hasClassReturn?s.assetShocks[assetClass]:0;
      if(!hasRowReturn&&!hasClassReturn&&valueLocal>0)issue(warnings,`${path}.localReturnPct`,'asset_return_assumed_zero','No holding-specific or matching asset-class return was entered. This holding is explicitly held constant in local-currency value.');
      const localReturnPct=numeric(rawReturn,`${path}.localReturnPct`,errors,{min:-100});
      if(c==='NOK'&&forwardRate!==null&&forwardRate!==1)issue(errors,`${path}.forwardRate`,'nok_identity','NOK/NOK forward must equal 1.');
      return{id,label,assetClass,currency:c,valueLocal,hedgePct,forwardRate,localReturnPct,...quote};
    });checkIds(parsed,errors,'rows');
    if(errors.length)return{...baseResult(errors,warnings),totals:null,rowResults:[]};
    const rowResults=parsed.map((r,i)=>{
      const q=(s.fxShocks[r.currency]===undefined?0:s.fxShocks[r.currency])/100,l=r.localReturnPct/100,scenarioSpot=r.spot*(1+q),initialValueNok=r.valueLocal*r.spot;
      if(!(scenarioSpot>0))issue(errors,`rows[${i}].scenarioSpot`,'numerical_range','The implied exchange rate must remain positive within numerical precision.');
      const hedgedAmount=r.valueLocal*r.hedgePct/100,scenarioValueLocal=r.valueLocal*(1+l),F=r.forwardRate===null?r.spot:r.forwardRate;
      const localAssetEffectNok=initialValueNok*l,fxTranslationEffectNok=initialValueNok*q,interactionEffectNok=initialValueNok*l*q,hedgeEffectNok=hedgedAmount*(F-scenarioSpot);
      const unhedgedValueNok=scenarioValueLocal*scenarioSpot,scenarioValueNok=unhedgedValueNok+hedgeEffectNok;
      const benchmarkValueNok=unhedgedValueNok+r.valueLocal*benchmarkHedgePct/100*(F-scenarioSpot);
      if(hedgedAmount>scenarioValueLocal+Math.max(1,r.valueLocal)*1e-12)issue(warnings,`rows[${i}]`,'hedge_exceeds_asset_value','Fixed initial-currency hedge exceeds the local asset value after the asset shock.');
      return{...r,initialValueNok,scenarioSpot,fxShockPct:q*100,scenarioValueLocal,hedgedAmount,localAssetEffectNok,fxTranslationEffectNok,interactionEffectNok,hedgeEffectNok,unhedgedValueNok,scenarioValueNok,
        changeNok:scenarioValueNok-initialValueNok,returnPct:initialValueNok===0?null:100*(scenarioValueNok/initialValueNok-1),benchmarkValueNok,activeVsBenchmarkNok:scenarioValueNok-benchmarkValueNok,
        residualExposureLocal:scenarioValueLocal-hedgedAmount};
    });
    const fields=['initialValueNok','scenarioValueNok','unhedgedValueNok','localAssetEffectNok','fxTranslationEffectNok','interactionEffectNok','hedgeEffectNok','changeNok','benchmarkValueNok','activeVsBenchmarkNok'];
    const totals=Object.fromEntries(fields.map(k=>[k,rowResults.reduce((a,r)=>a+r[k],0)]));
    totals.returnPct=totals.initialValueNok===0?null:100*totals.changeNok/totals.initialValueNok;
    totals.benchmarkChangeNok=totals.benchmarkValueNok-totals.initialValueNok;
    totals.benchmarkReturnPct=totals.initialValueNok===0?null:100*totals.benchmarkChangeNok/totals.initialValueNok;
    totals.activeVsBenchmarkPct=totals.initialValueNok===0?null:100*totals.activeVsBenchmarkNok/totals.initialValueNok;
    finiteOutput({totals,rowResults},errors);
    if(errors.length)return{...baseResult(errors,warnings),totals:null,rowResults:[]};
    return{...baseResult(errors,warnings),totals,rowResults,benchmark:{type:'same_holdings_currency_policy',hedgePct:benchmarkHedgePct,assumed:true,label:`Same holdings, assumed ${benchmarkHedgePct}% currency hedge`},
      interpretation:'Hypothetical end-horizon asset value plus the payoff of a fixed initial-currency hedge. Same local holdings and shocks in the benchmark; no actual NBIM holdings or official benchmark are implied. This is not live derivative mark-to-market.'};
  }
  function collateral(positions,market,scenario,agreements) {
    const errors=[],warnings=[],s=readScenario(scenario,errors),rawPositions=checkArray(positions,'positions',errors,true);
    const rules=new Map();
    checkArray(agreements===undefined?[]:agreements,'agreements',errors,true).forEach((raw,i)=>{
      const a=object(raw)?raw:{},path=`agreements[${i}]`;
      const entity=string(a.entity,`${path}.entity`,errors,true),csaId=string(a.csaId,`${path}.csaId`,errors,true),key=JSON.stringify([entity,csaId]);
      if(rules.has(key))issue(errors,path,'duplicate_agreement','Only one agreement per entity and CSA ID is permitted.');
      const fields={};for(const k of ['thresholdNok','minimumTransferNok','postedCollateralNok','eligibleCollateralNok'])fields[k]=numeric(a[k],`${path}.${k}`,errors,{min:0});
      fields.haircutPct=numeric(a.haircutPct,`${path}.haircutPct`,errors,{min:0,max:100});rules.set(key,{entity,csaId,...fields});
    });
    const rate=s.discountRatePct===undefined?null:numeric(s.discountRatePct,'scenario.discountRatePct',errors);
    const parsed=rawPositions.map((raw,i)=>{
      const p=object(raw)?raw:{},path=`positions[${i}]`;
      if(!object(raw))issue(errors,path,'object_required','A hedge position must be an object.');
      const id=string(p.id,`${path}.id`,errors,true),entity=string(p.entity,`${path}.entity`,errors,true),csaId=string(p.csaId,`${path}.csaId`,errors,false),c=currency(p.currency,`${path}.currency`,errors);
      if(!['buy','sell'].includes(p.direction))issue(errors,`${path}.direction`,'direction_required','Choose buy or sell foreign currency.');
      const notional=numeric(p.notional,`${path}.notional`,errors,{min:0}),forwardRate=numeric(p.forwardRate,`${path}.forwardRate`,errors,{positive:true}),quote=readMarket(market,c,errors,warnings);
      const stressForwardRate=absent(p.stressForwardRate)?null:numeric(p.stressForwardRate,`${path}.stressForwardRate`,errors,{positive:true});
      let discountFactor=1,maturityDate=null;
      if(p.maturityDate!==undefined)maturityDate=date(p.maturityDate,`${path}.maturityDate`,errors,true);
      if(s.valuationDate&&maturityDate&&maturityDate<s.valuationDate)issue(errors,`${path}.maturityDate`,'expired_position','An expired hedge is not a prospective collateral position.');
      if(!absent(p.discountFactor))discountFactor=numeric(p.discountFactor,`${path}.discountFactor`,errors,{positive:true});
      else if(stressForwardRate!==null&&rate!==null){
        if(!s.valuationDate||!maturityDate)issue(errors,path,'discount_dates_required','A discount rate requires valuationDate and maturityDate.');
        else{
          const years=(Date.parse(maturityDate+'T00:00:00Z')-Date.parse(s.valuationDate+'T00:00:00Z'))/DAY_MS/365;
          if(years<0)issue(errors,`${path}.maturityDate`,'expired_position','Maturity must not precede the valuation date.');
          discountFactor=Math.exp(-rate/100*years);
          if(!(discountFactor>0)&&Number.isFinite(discountFactor))issue(errors,`${path}.discountFactor`,'numerical_range','The implied discount factor underflows the numerical range.');
        }
      }
      if(stressForwardRate!==null&&absent(p.discountFactor)&&rate===null)issue(warnings,path,'undiscounted_forward_mark','Stress-forward mark uses discount factor 1 because no discount factor or dated rate was supplied.');
      if(stressForwardRate===null)issue(warnings,path,'payoff_proxy_only','No stressed remaining-tenor forward is supplied. This is an undiscounted terminal-payoff proxy, not current mark-to-market or a forecast of margin calls.');
      if(c==='NOK'&&(forwardRate!==1||(stressForwardRate!==null&&stressForwardRate!==1)))issue(errors,path,'nok_identity','NOK/NOK forward rates must equal 1.');
      return{id,entity,csaId,currency:c,direction:p.direction,notional,forwardRate,stressForwardRate,discountFactor,maturityDate,...quote};
    });checkIds(parsed,errors,'positions');
    if(errors.length)return{...baseResult(errors,warnings),positions:[],groups:[],totals:null,completeMarginTerms:false};
    const results=parsed.map(p=>{
      const sign=p.direction==='buy'?1:-1,scenarioSpot=p.spot*(1+(s.fxShocks[p.currency]||0)/100),proxy=p.stressForwardRate===null;
      return{...p,scenarioSpot,markNok:sign*p.notional*((proxy?scenarioSpot:p.stressForwardRate)-p.forwardRate)*(proxy?1:p.discountFactor),valuationMode:proxy?'undiscounted_terminal_payoff_proxy':'stress_forward_mark',appliedDiscountFactor:proxy?1:p.discountFactor};
    });
    const grouped=new Map();
    results.forEach(p=>{
      const key=JSON.stringify(p.csaId?[p.entity,p.csaId]:[p.entity,'unnetted',p.id]);
      if(!grouped.has(key))grouped.set(key,{key,entity:p.entity,csaId:p.csaId,positionIds:[],netMarkNok:0,containsProxy:false});
      const g=grouped.get(key);g.positionIds.push(p.id);g.netMarkNok+=p.markNok;g.containsProxy=g.containsProxy||p.valuationMode==='undiscounted_terminal_payoff_proxy';
    });
    const groups=[...grouped.values()].map(g=>{
      const rule=g.csaId?rules.get(JSON.stringify([g.entity,g.csaId])):null;
      if(!rule){issue(warnings,`CSA:${g.entity}:${g.csaId||'not supplied'}`,'margin_terms_unknown','Margin terms are unknown. No zero-threshold collateral obligation or cross-position netting is invented.');return{...g,termsKnown:false,requiredCollateralNok:null,marginCallNok:null,eligibleAfterHaircutNok:null,eligibleCollateralUsedNok:null,immediateCashNeedNok:null};}
      const requiredCollateralNok=Math.max(0,-g.netMarkNok-rule.thresholdNok),incremental=Math.max(0,requiredCollateralNok-rule.postedCollateralNok);
      const marginCallNok=incremental>=rule.minimumTransferNok?incremental:0,eligibleAfterHaircutNok=rule.eligibleCollateralNok*(1-rule.haircutPct/100),eligibleCollateralUsedNok=Math.min(marginCallNok,eligibleAfterHaircutNok);
      return{...g,...rule,termsKnown:true,requiredCollateralNok,incrementalBeforeMtaNok:incremental,marginCallNok,eligibleAfterHaircutNok,eligibleCollateralUsedNok,immediateCashNeedNok:Math.max(0,marginCallNok-eligibleAfterHaircutNok),potentialCollateralReleaseNok:Math.max(0,rule.postedCollateralNok-requiredCollateralNok)};
    });
    const totals={netMarkNok:groups.reduce((a,g)=>a+g.netMarkNok,0),knownMarginCallNok:0,eligibleCollateralUsedNok:0,immediateCashNeedNok:0,unassessedAdverseMarkNok:0,potentialCollateralReleaseNok:0};
    groups.forEach(g=>{if(g.termsKnown){totals.knownMarginCallNok+=g.marginCallNok;totals.eligibleCollateralUsedNok+=g.eligibleCollateralUsedNok;totals.immediateCashNeedNok+=g.immediateCashNeedNok;totals.potentialCollateralReleaseNok+=g.potentialCollateralReleaseNok;}else totals.unassessedAdverseMarkNok+=Math.max(0,-g.netMarkNok);});
    finiteOutput({totals,positions:results,groups},errors);
    if(errors.length)return{...baseResult(errors,warnings),positions:[],groups:[],totals:null,completeMarginTerms:false};
    return{...baseResult(errors,warnings),positions:results,groups,totals,completeMarginTerms:groups.every(g=>g.termsKnown),containsProxy:groups.some(g=>g.containsProxy),
      interpretation:'Potential incremental collateral/cash requirement under entered CSA assumptions. Proxy-based amounts are stress illustrations, not live margin calls. Existing posted collateral and separately allocated eligible collateral are not an economic loss; do not add margin calls again to terminal treasury cash flow. No release or cross-CSA surplus funds another group automatically.'};
  }
  function validateTreasury(rows,market,scenario,options){const r=treasury(rows,market,scenario,options);return{version:VERSION,valid:r.valid,errors:r.errors,warnings:r.warnings};}
  return Object.freeze({version:VERSION,treasury,validateTreasury,comparePolicies,reverseStress,commonFxThreshold,portfolio,collateral});
});
