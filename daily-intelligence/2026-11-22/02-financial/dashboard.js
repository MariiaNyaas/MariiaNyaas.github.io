/* EUR/NOK Research Lab. No external dependencies. All empirical values come from
   the retained model output; scenarios and treasury arithmetic are separate. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const fmt = (value, digits = 2) => finite(value) ? value.toLocaleString('en-GB', {minimumFractionDigits:digits, maximumFractionDigits:digits}) : '—';
  const signed = (value, digits = 3) => finite(value) ? `${value > 0 ? '+' : ''}${fmt(value, digits)}` : '—';
  const percent = value => finite(value) ? `${fmt(value * 100, 1)}%` : '—';
  const $empty = (id, message) => { $(id).innerHTML = `<div class="empty">${esc(message)}</div>`; };
  const safeUrl = url => /^(https?:\/\/|\.\.?\/|model\/)/i.test(String(url)) ? String(url) : '';
  const state = {results:null, predictions:{}, eventStudy:null, horizon:'1', model:'rw', scenarioInputs:{}, scenarioSpot:null, treasuryInitialized:false};
  const hdata = () => state.results?.horizons?.[state.horizon] || {};
  const selectedModel = () => (hdata().models || []).find(m => m.id === state.model);
  const horizonName = () => `${state.horizon} ${state.horizon === '1' ? 'month' : 'months'}`;
  const tone = value => finite(value) && value > 0 ? 'positive-text' : finite(value) && value < 0 ? 'negative-text' : '';
  const download = (filename, data, type = 'application/json') => {
    const blob = new Blob([typeof data === 'string' ? data : JSON.stringify(data, null, 2)], {type});
    const url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const csv = rows => rows.map(row => row.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n');
  const short = (text, length = 30) => String(text).length > length ? `${String(text).slice(0, length - 1)}…` : String(text);
  const svgStart = (w, h, title) => `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><title>${esc(title)}</title>`;
  const tickValues = (min, max, n = 4) => Array.from({length:n + 1}, (_, i) => min + (max - min) * i / n);
  const extent = (values, includeZero = true) => {
    const clean = values.filter(finite);
    if (!clean.length) return [-1, 1];
    let min = Math.min(...clean), max = Math.max(...clean);
    if (includeZero) { min = Math.min(0, min); max = Math.max(0, max); }
    if (min === max) { min -= 1; max += 1; }
    const pad = (max - min) * .09; return [min - pad, max + pad];
  };
  function barChart(id, rows, title, signedScale = false) {
    if (!rows.length) return $empty(id, 'No comparable results are retained for this horizon.');
    const w = 640, left = 220, right = 58, top = 22, step = 41, bottom = 40, h = top + rows.length * step + bottom;
    const vals = rows.map(r => r.value).filter(finite);
    const low = signedScale ? Math.min(0, ...vals) : 0;
    const high = Math.max(0, ...vals), span = high - low || 1;
    const min = signedScale ? low - span * .08 : 0, max = high + span * .13;
    const x = v => left + (v - min) / (max - min || 1) * (w - left - right);
    let s = svgStart(w, h, title);
    for (const t of tickValues(min, max, 4)) s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${top - 8}" y2="${h - bottom + 3}"/><text class="axis-label" text-anchor="middle" x="${x(t)}" y="${h - 13}">${fmt(t, 2)}</text>`;
    s += `<line class="zero" x1="${x(0)}" x2="${x(0)}" y1="${top - 8}" y2="${h - bottom + 3}"/>`;
    rows.forEach((r, i) => {
      const y = top + i * step;
      s += `<text class="${r.id === state.model ? 'label-strong' : ''}" x="0" y="${y + 20}"><title>${esc(r.label)}</title>${esc(short(r.label, 29))}</text>`;
      if (finite(r.value)) {
        const xv = x(r.value), width = Math.max(1, Math.abs(xv - x(0))), fill = signedScale ? (r.value >= 0 ? 'var(--green)' : 'var(--red)') : r.id === state.model ? 'var(--gold)' : r.id === 'rw' ? 'var(--subtle)' : '#62849c';
        s += `<rect x="${Math.min(xv, x(0))}" y="${y + 3}" width="${width}" height="25" rx="2" fill="${fill}" opacity="${r.id === state.model ? 1 : .82}"><title>${esc(r.label)}: ${fmt(r.value, 4)} percentage points</title></rect><text class="label-strong" x="${r.value >= 0 ? xv + 7 : xv - 7}" text-anchor="${r.value >= 0 ? 'start' : 'end'}" y="${y + 21}">${signedScale ? signed(r.value, 3) : fmt(r.value, 3)}</text>`;
      }
    });
    $(id).innerHTML = s + '</svg>';
  }
  function ciChart(id, rows, title) {
    rows = rows.filter(r => finite(r.value));
    if (!rows.length) return $empty(id, 'No uncertainty interval is retained for this comparison.');
    const w = 640, left = 220, right = 36, top = 24, step = 41, bottom = 40, h = top + rows.length * step + bottom;
    const [min, max] = extent(rows.flatMap(r => [r.value, ...(r.ci || [])])), x = v => left + (v - min) / (max - min) * (w - left - right);
    let s = svgStart(w, h, title);
    for (const t of tickValues(min, max)) s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${top - 9}" y2="${h - bottom + 4}"/><text class="axis-label" x="${x(t)}" y="${h - 13}" text-anchor="middle">${fmt(t, 2)}</text>`;
    s += `<line class="zero" x1="${x(0)}" x2="${x(0)}" y1="${top - 9}" y2="${h - bottom + 4}"/>`;
    rows.forEach((r, i) => {
      const y = top + i * step + 14;
      const color = r.id === state.model ? 'var(--gold)' : 'var(--muted)';
      s += `<text x="0" y="${y + 5}" class="${r.id === state.model ? 'label-strong' : ''}"><title>${esc(r.label)}</title>${esc(short(r.label, 29))}</text>`;
      if (Array.isArray(r.ci) && r.ci.length >= 2 && r.ci.every(finite)) s += `<line x1="${x(r.ci[0])}" x2="${x(r.ci[1])}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="2"/><line x1="${x(r.ci[0])}" x2="${x(r.ci[0])}" y1="${y - 5}" y2="${y + 5}" stroke="${color}"/><line x1="${x(r.ci[1])}" x2="${x(r.ci[1])}" y1="${y - 5}" y2="${y + 5}" stroke="${color}"/>`;
      s += `<circle cx="${x(r.value)}" cy="${y}" r="4.7" fill="${color}"><title>${esc(r.label)}: ${signed(r.value)} pp; 95% interval ${r.ci ? r.ci.map(v => fmt(v, 3)).join(' to ') : 'not reported'}</title></circle>`;
    });
    $(id).innerHTML = s + '</svg>';
  }
  function lineChart(id, rows, series, title, options = {}) {
    if (!rows.length) return $empty(id, 'No historical predictions are available for this model and horizon.');
    const w = 1120, h = 315, left = 61, right = 25, top = 25, bottom = 48;
    const all = rows.flatMap(row => series.map(s => row[s.key])).filter(finite), [min, max] = extent(all);
    const x = i => left + i / Math.max(1, rows.length - 1) * (w - left - right), y = v => top + (max - v) / (max - min) * (h - top - bottom);
    let s = svgStart(w, h, title);
    for (const t of tickValues(min, max)) s += `<line class="grid" x1="${left}" x2="${w - right}" y1="${y(t)}" y2="${y(t)}"/><text class="axis-label" x="${left - 10}" y="${y(t) + 4}" text-anchor="end">${fmt(t, options.currency ? 0 : 1)}</text>`;
    if (min < 0 && max > 0) s += `<line class="zero" x1="${left}" x2="${w - right}" y1="${y(0)}" y2="${y(0)}"/>`;
    for (let i = 0; i < Math.min(7, rows.length); i++) {
      const at = Math.round(i * (rows.length - 1) / Math.max(1, Math.min(7, rows.length) - 1));
      s += `<text class="axis-label" x="${x(at)}" y="${h - 18}" text-anchor="${i === 0 ? 'start' : i === Math.min(7, rows.length) - 1 ? 'end' : 'middle'}">${esc(rows[at].label || rows[at].target || rows[at].origin)}</text>`;
    }
    series.forEach(ser => {
      let path = '', continuous = false;
      rows.forEach((r, i) => { if (finite(r[ser.key])) { path += `${continuous ? 'L' : 'M'}${x(i).toFixed(2)},${y(r[ser.key]).toFixed(2)} `; continuous = true; } else continuous = false; });
      s += `<path d="${path}" fill="none" stroke="${ser.color}" stroke-width="${ser.width || 2}" stroke-linejoin="round" opacity="${ser.opacity || 1}"/>`;
      rows.forEach((r, i) => { if (finite(r[ser.key])) s += `<circle cx="${x(i)}" cy="${y(r[ser.key])}" r="4" fill="transparent"><title>${esc(r.target || r.label || r.origin)} — ${esc(ser.label)}: ${fmt(r[ser.key], 4)}</title></circle>`; });
    });
    $(id).innerHTML = s + '</svg>';
  }
  function showTab(tab, focus = false) {
    document.querySelectorAll('[data-tab]').forEach(button => {
      const active = button.dataset.tab === tab;
      button.setAttribute('aria-selected', String(active)); button.tabIndex = active ? 0 : -1;
      const panel = $(`panel-${button.dataset.tab}`); panel.hidden = !active; panel.classList.toggle('hidden', !active);
      if (active && focus) button.focus();
    });
    if (tab === 'treasury') renderTreasury();
    if (tab === 'scenarios') renderScenarioValue();
    document.querySelector('.toolbar').classList.toggle('hidden',tab==='events');
  }
  function metadata() {
    const meta = state.results.metadata || {};
    $('version-label').textContent = meta.as_of ? `UPDATED ${meta.as_of}` : 'MULTIDIMENSIONAL MODEL';
    $('sample-label').textContent = `${meta.sample_start || '—'} to ${meta.sample_end || '—'} · ${meta.validation_label || 'Historical walk-forward evaluation'}`;
    $('snapshot-warning').textContent = meta.forecast_timestamp_warning || 'Research snapshot; the retained fixing is not a live executable quote.';
    $('footer-date').textContent = `Research snapshot ${meta.as_of || meta.sample_end || 'date not reported'}. Positive EUR/NOK change means a weaker Norwegian krone.`;
    if (!state.treasuryInitialized && finite(meta.latest_spot)) {
      $('treasury-reference').value = meta.latest_spot.toFixed(4); $('treasury-future').value = meta.latest_spot.toFixed(4); state.treasuryInitialized = true;
    }
  }
  function renderKpis() {
    const meta = state.results.metadata || {}, models = hdata().models || [], model = selectedModel();
    const list = [
      ['Last observed EUR/NOK', fmt(meta.latest_spot, 4), `NOK per EUR · ${meta.latest_origin || meta.sample_end || 'retained snapshot'}`],
      ['Model specifications', String(models.length), 'Benchmarks and candidate models'],
      ['Evaluation observations', model?.n ? String(model.n) : '—', 'Selected model and horizon'],
      ['Forecast horizon', horizonName(), 'Cumulative log currency change']
    ];
    $('summary-kpis').innerHTML = list.map(([label,value,note]) => `<div class="kpi"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
  }
  function renderEvidence() {
    const data = hdata(), models = data.models || [], model = selectedModel(), ar = models.find(m => m.id === 'ar1');
    barChart('mae-chart', models.map(m => ({id:m.id, label:m.label, value:m.mae})), 'Mean absolute forecast error by model');
    ciChart('ci-chart', models.filter(m => m.id !== 'rw').map(m => ({id:m.id,label:m.label,value:m.improvement_vs_rw,ci:m.improvement_ci})), 'Mean error improvement and 95% interval against random walk');
    $('comparison-table').innerHTML = `<table><caption class="hidden">Model comparison for ${esc(horizonName())}</caption><thead><tr><th>Model</th><th class="number">MAE, pp</th><th class="number">RMSE, pp</th><th class="number">Direction</th><th class="number">Gain vs random walk, pp</th><th class="number">Gain vs own history, pp</th><th class="number">95% interval vs RW</th><th class="number">N</th></tr></thead><tbody>${models.map(m => `<tr class="${m.id === state.model ? 'selected' : ''}"><td><button class="table-link" type="button" data-select-model="${esc(m.id)}">${esc(m.label)}</button>${m.id === 'rw' || m.id === 'ar1' ? '<span class="badge">BASELINE</span>' : ''}</td><td class="number">${fmt(m.mae,3)}</td><td class="number">${fmt(m.rmse,3)}</td><td class="number">${m.id === 'rw' ? '—' : percent(m.direction_accuracy)}</td><td class="number ${tone(m.improvement_vs_rw)}">${m.id === 'rw' ? '—' : signed(m.improvement_vs_rw)}</td><td class="number ${tone(finite(ar?.mae) && finite(m.mae) ? ar.mae - m.mae : null)}">${m.id === 'ar1' || !finite(ar?.mae) ? '—' : signed(ar.mae - m.mae)}</td><td class="number">${Array.isArray(m.improvement_ci) && m.id !== 'rw' ? m.improvement_ci.map(x=>fmt(x,3)).join(' to ') : '—'}</td><td class="number">${esc(m.n ?? '—')}</td></tr>`).join('')}</tbody></table>`;
    document.querySelectorAll('[data-select-model]').forEach(button => button.addEventListener('click', () => { state.model = button.dataset.selectModel; $('model-select').value = state.model; renderAll(); }));
    const allModels=Object.values(state.results.horizons).flatMap(h=>h.models||[]).filter(m=>m.id!=='rw');
    const adjustedEvidence=allModels.some(m=>m.improvement_vs_rw>0&&finite(m.p_rw_holm)&&m.p_rw_holm<.05);
    $('research-status').classList.toggle('positive', adjustedEvidence);
    const title = adjustedEvidence ? 'Historical evidence requires prospective confirmation' : 'No validated forecasting edge';
    const description = adjustedEvidence ? 'At least one declared comparison survives the reported multiple-testing adjustment. A genuinely prospective test is still required before changing the decision reference.' : 'No candidate establishes a forecasting advantage after the declared evidence checks. Keep the random walk as the decision reference; use the full model for diagnostic scenarios.';
    $('research-status').innerHTML = `<strong>${esc(title)}</strong><span>${esc(description)}</span>`;
    const best = models.filter(m=>finite(m.mae)).reduce((a,b)=>!a||b.mae<a.mae?b:a,null);
    const holm=state.results.multiplicity;
    $('evidence-reading').innerHTML = `<strong>How to read this:</strong> ${best ? `${esc(best.label)} has the lowest observed MAE in this comparison (${fmt(best.mae,3)} pp). ` : ''}A ranking is not a validation decision. Whiskers are nominal intervals.${holm?` ${esc(holm.method)} adjustment covers ${esc(holm.family_size)} declared comparisons across horizons; ${finite(model?.p_rw_holm)?`the selected model’s adjusted p-value versus the random walk is ${fmt(model.p_rw_holm,3)}`:'the random walk is the reference'} and does not establish a validated edge.`:''} “Gain vs own history” compares against the autoregressive baseline. Positive EUR/NOK returns mean NOK depreciation.`;
    const coverage=model?.interval_coverage,under=finite(coverage)&&coverage<.8;
    $('band-reliability').classList.toggle('undercoverage',under);
    $('band-reliability').innerHTML=`<strong>${under?'Undercoverage: do not use as a risk limit':'Historical residual-band reliability'}</strong><div class="band-metrics"><span>Selected model<br><b>${esc(model?.label||'—')}</b></span><span>Observed band coverage<br><b>${percent(coverage)}</b></span><span>Evaluated intervals<br><b>${esc(model?.interval_n??'—')}</b></span><span>Residual percentile span<br><b>5th–95th</b></span></div>The band endpoints come from prior matured residuals; a 5th–95th percentile span does not guarantee 90% future coverage. Use explicit stress assumptions in the treasury calculator.`;
    const latest=data.latest_forecasts||[],meta=state.results.metadata||{},spot=meta.latest_spot;
    $('snapshot-table-note').textContent=`${meta.forecast_timestamp_warning||'Retained model outputs, not live executable quotes.'} Origin ${meta.latest_origin||'—'}; horizon ${horizonName()}. Historical residual bands use 5th–95th percentiles. They have no coverage guarantee and are not risk limits.`;
    $('latest-table').innerHTML=`<table><thead><tr><th>Model</th><th>Target month</th><th class="number">Fitted log change, %</th><th class="number">Implied EUR/NOK</th><th class="number">Empirical spot range</th><th class="number">Prior residuals</th></tr></thead><tbody>${latest.map(f=>`<tr class="${f.model_id===state.model?'selected':''}"><td>${esc(f.label)}</td><td>${esc(f.target_month)}</td><td class="number">${signed(f.prediction,3)}</td><td class="number">${finite(spot)&&finite(f.prediction)?fmt(spot*Math.exp(f.prediction/100),4):'—'}</td><td class="number">${finite(spot)&&finite(f.lower)&&finite(f.upper)?`${fmt(spot*Math.exp(f.lower/100),4)} – ${fmt(spot*Math.exp(f.upper/100),4)}`:'Not available'}</td><td class="number">${esc(f.calibration_n??'—')}</td></tr>`).join('')}</tbody></table>`;
  }
  function renderDrivers() {
    const blocks = [
      ['Currency history','Own momentum and volatility','The baseline for incremental information.'],
      ['Relative rates','Norway versus the euro area','Rate levels and changes, with explicit policy conventions.'],
      ['Energy & global risk','Oil, market stress and the dollar','External conditions facing a small open economy.'],
      ['Relative inflation','Comparable consumer-price measures','Lagged according to the stated availability rule.']
    ];
    $('feature-groups').innerHTML = blocks.map(([title,desc,note])=>`<article class="dimension-card"><h3>${esc(title)}</h3><p>${esc(desc)}</p><small>${esc(note)}</small></article>`).join('');
    const rows = hdata().ablations || [];
    ciChart('ablation-chart', rows.map(r=>({id:r.block,label:r.label,value:r.incremental_gain,ci:r.ci})), 'Incremental contribution of feature blocks');
    if (!rows.length) { $empty('ablation-table','No feature-block ablation is retained for this horizon.'); return; }
    $('ablation-table').innerHTML = `<table><thead><tr><th>Block tested</th><th class="number">MAE with block, pp</th><th class="number">MAE without block, pp</th><th class="number">Incremental gain, pp</th><th class="number">95% interval</th><th>Reading</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.label)}</td><td class="number">${fmt(r.full_mae,3)}</td><td class="number">${fmt(r.without_mae,3)}</td><td class="number ${tone(r.incremental_gain)}">${signed(r.incremental_gain)}</td><td class="number">${Array.isArray(r.ci)?r.ci.map(v=>fmt(v,3)).join(' to '):'—'}</td><td>${Array.isArray(r.ci) ? r.ci[0]>0 ? 'Positive nominal interval' : r.ci[1]<0 ? 'Block worsens accuracy' : 'Interval spans zero' : 'Interval not reported'}</td></tr>`).join('')}</tbody></table>`;
  }
  function renderPath() {
    const rows = (state.predictions[state.horizon]?.[state.model] || []).filter(r=>finite(r.actual)&&finite(r.predicted));
    const model = selectedModel();
    $('path-description').textContent = `${model?.label || 'Selected model'} · ${horizonName()} cumulative log change (%). Positive values indicate NOK depreciation.`;
    lineChart('forecast-chart', rows, [{key:'actual',label:'Observed',color:'var(--muted)',width:1.6,opacity:.8},{key:'predicted',label:'Predicted',color:'var(--gold)',width:2.2}], 'Observed and predicted EUR/NOK changes');
    let sum=0;
    const loss = rows.map(r=>{ sum += Math.abs(r.actual-(finite(r.baseline)?r.baseline:0))-Math.abs(r.actual-r.predicted); return {...r,cumulative:sum}; });
    lineChart('loss-chart',loss,[{key:'cumulative',label:'Cumulative error improvement',color:'var(--gold)',width:2.3}],'Cumulative error improvement against random walk');
    const regimes = (hdata().regimes || []).filter(r=>!r.model_id||r.model_id===state.model);
    if (!regimes.length) { $empty('regime-table','No regime breakdown is retained for the selected model.'); return; }
    $('regime-table').innerHTML = `<table><thead><tr><th>Regime / subsample</th><th class="number">N</th><th class="number">Model MAE, pp</th><th class="number">Random-walk MAE, pp</th><th class="number">Gain, pp</th></tr></thead><tbody>${regimes.map(r=>`<tr><td>${esc(r.regime||r.label)}${r.small_sample?'<span class="badge">SMALL SAMPLE</span>':''}</td><td class="number">${esc(r.n??'—')}</td><td class="number">${fmt(r.mae,3)}</td><td class="number">${fmt(r.baseline_mae,3)}</td><td class="number ${tone(r.gain)}">${signed(r.gain)}</td></tr>`).join('')}</tbody></table>`;
  }
  function scenarioFeatures() { return (hdata().scenario?.features || []).filter(f=>finite(f.value)&&finite(f.coefficient)); }
  function scenarioValue(overrides={}) {
    const scenario=hdata().scenario; if(!scenario||!finite(scenario.baseline_prediction))return null;
    const values = {...state.scenarioInputs[state.horizon],...overrides};
    let prediction=scenario.baseline_prediction;
    for(const f of scenarioFeatures()){
      const value=Object.hasOwn(values,f.name)?values[f.name]:f.value;
      if(!finite(value))return null;
      prediction+=f.coefficient*(value-f.value);
    }
    const spot=scenario.origin_spot||state.results.metadata?.latest_spot;
    if(!finite(spot)||spot<=0||!finite(prediction))return null;
    const implied=spot*Math.exp(prediction/100),reference=spot*Math.exp(scenario.baseline_prediction/100);
    if(!finite(implied)||implied<=0||!finite(reference)||reference<=0)return null;
    return {prediction,spot:implied,reference,origin_spot:spot};
  }
  function renderScenarioControls() {
    const scenario=hdata().scenario, features=scenarioFeatures();
    const available=!!scenario&&features.length>0&&finite(scenario.baseline_prediction);
    $('scenario-workspace').classList.toggle('hidden',!available);$('scenario-unavailable').classList.toggle('hidden',available);
    if(!available){$('scenario-unavailable').textContent='A fitted conditional sensitivity model is not retained for this horizon. The historical evidence and user-defined treasury calculator remain available.';return;}
    const values=state.scenarioInputs[state.horizon] ||= Object.fromEntries(features.map(f=>[f.name,f.value]));
    $('scenario-controls').innerHTML=features.map((f,i)=>`<label for="scenario-feature-${i}">${esc(f.label||f.name)}${f.unit?` <span class="metric-note">${esc(f.unit)}</span>`:''}<input id="scenario-feature-${i}" data-feature="${esc(f.name)}" type="number" step="any" value="${finite(values[f.name])?values[f.name]:Object.hasOwn(values,f.name)?'':f.value}" inputmode="decimal"><small>Observed: ${fmt(f.value,3)} · fitted coefficient: ${signed(f.coefficient,4)}</small></label>`).join('');
    document.querySelectorAll('[data-feature]').forEach(input=>input.addEventListener('input',()=>{const value=Number(input.value);values[input.dataset.feature]=input.value.trim()!==''&&finite(value)?value:null;input.setAttribute('aria-invalid',String(values[input.dataset.feature]===null));renderScenarioValue();}));
    const previousX=$('surface-x').value,previousY=$('surface-y').value;
    const opts=features.map(f=>`<option value="${esc(f.name)}">${esc(f.label||f.name)}</option>`).join('');
    $('surface-x').innerHTML=opts;$('surface-y').innerHTML=opts;
    $('surface-x').value=features.some(f=>f.name===previousX)?previousX:features[0].name;
    $('surface-y').value=features.some(f=>f.name===previousY)&&previousY!==$('surface-x').value?previousY:features[Math.min(1,features.length-1)].name;
    const full=(hdata().models||[]).find(m=>m.id===scenario.model_id);
    $('scenario-band-note').textContent=`${scenario.label||'Retained linear model'} · ${horizonName()}. Diagnostic use only: no validated edge. The 5th–95th residual band uses up to 60 matured prior errors (at least 24). Observed historical coverage: ${percent(full?.interval_coverage)} across ${full?.interval_n??'—'} intervals. Do not use this band as a risk limit.`;
    renderScenarioValue();
  }
  function renderScenarioValue() {
    if(!state.results)return;
    const value=scenarioValue();
    $('use-scenario-treasury').disabled=!value;$('export-scenario').disabled=!value;
    if(!value){
      state.scenarioSpot=null;
      ['scenario-spot','scenario-reference','scenario-change','scenario-return','scenario-band'].forEach(id=>{$(id).textContent='—';});
      $('scenario-warning').textContent='Invalid scenario input. Enter a finite number in every field and reduce extreme inputs. The implied exchange rate must be finite and positive; no prior result is retained.';
      $empty('scenario-surface','A valid scenario is required before the sensitivity surface can be calculated.');
      return;
    }
    state.scenarioSpot=value.spot;
    $('scenario-spot').textContent=fmt(value.spot,4);$('scenario-reference').textContent=fmt(value.reference,4);
    $('scenario-change').textContent=`${signed(value.prediction-hdata().scenario.baseline_prediction,3)} pp`;
    $('scenario-return').textContent=`${signed(value.prediction,3)}%`;
    const q=hdata().scenario.residual_quantiles;
    const band=Array.isArray(q)&&q.length===2&&q.every(finite)?q.map(v=>value.origin_spot*Math.exp((value.prediction+v)/100)):null;
    $('scenario-band').textContent=band&&band.every(v=>finite(v)&&v>0)?band.map(v=>fmt(v,3)).join(' – '):band?'Outside numerical range':'Not reported';
    const features=scenarioFeatures(),out=features.filter(f=>{const v=state.scenarioInputs[state.horizon]?.[f.name]??f.value;return finite(f.min)&&v<f.min||finite(f.max)&&v>f.max;});
    $('scenario-warning').innerHTML=out.length?`<strong>Outside the stated input range:</strong> ${esc(out.map(f=>f.label||f.name).join(', '))}. Treat the result as extrapolation. The fitted equation does not model market feedback or structural breaks.`:'These inputs are varied jointly while other features are held fixed. Historical associations can change across regimes. The fitted equation does not model market feedback, an identified policy surprise or a structural economic response.';
    renderSurface();
  }
  function renderSurface() {
    const base=scenarioValue();
    if(!base){$empty('scenario-surface','A valid scenario is required before the sensitivity surface can be calculated.');return;}
    const features=scenarioFeatures(),fx=features.find(f=>f.name===$('surface-x').value),fy=features.find(f=>f.name===$('surface-y').value);
    if(!fx||!fy||fx.name===fy.name){$empty('scenario-surface','Choose two different dimensions to display the sensitivity surface.');return;}
    const inputs=state.scenarioInputs[state.horizon]||{},centerX=inputs[fx.name]??fx.value,centerY=inputs[fy.name]??fy.value;
    const range=f=>finite(f.min)&&finite(f.max)&&f.max>f.min?(f.max-f.min)/4:Math.max(Math.abs(f.value)*.3,finite(f.step)?f.step*5:1);
    const rx=range(fx),ry=range(fy),n=7,w=850,h=520,left=130,right=35,top=27,bottom=115,cw=(w-left-right)/n,ch=(h-top-bottom)/n;
    const xs=Array.from({length:n},(_,i)=>centerX-rx+2*rx*i/(n-1)),ys=Array.from({length:n},(_,i)=>centerY+ry-2*ry*i/(n-1));
    const cells=ys.flatMap((yv,yi)=>xs.map((xv,xi)=>({xv,yv,xi,yi,value:scenarioValue({[fx.name]:xv,[fy.name]:yv})}))),maxDiff=Math.max(.001,...cells.filter(c=>c.value).map(c=>Math.abs(c.value.spot-base.spot)));
    let s=svgStart(w,h,`Conditional EUR/NOK surface: ${fx.label||fx.name} and ${fy.label||fy.name}`);
    cells.forEach(c=>{const diff=c.value?c.value.spot-base.spot:0,a=.1+.45*Math.abs(diff)/maxDiff,color=!c.value?'var(--line)':diff>=0?`rgba(229,154,148,${a})`:`rgba(123,196,175,${a})`;s+=`<rect x="${left+c.xi*cw}" y="${top+c.yi*ch}" width="${cw-2}" height="${ch-2}" fill="${color}" rx="2"><title>${esc(fx.label||fx.name)} ${fmt(c.xv,3)}; ${esc(fy.label||fy.name)} ${fmt(c.yv,3)}; ${c.value?'conditional EUR/NOK '+fmt(c.value.spot,4):'outside numerical range'}</title></rect><text class="label-strong" x="${left+(c.xi+.5)*cw-1}" y="${top+(c.yi+.5)*ch+4}" text-anchor="middle">${c.value?fmt(c.value.spot,3):'N/A'}</text>`;});
    xs.forEach((v,i)=>{s+=`<text class="axis-label" x="${left+(i+.5)*cw}" y="${h-bottom+25}" text-anchor="middle">${fmt(v,2)}</text>`;});
    ys.forEach((v,i)=>{s+=`<text class="axis-label" x="${left-13}" y="${top+(i+.5)*ch+4}" text-anchor="end">${fmt(v,2)}</text>`;});
    s+=`<text x="${left+(w-left-right)/2}" y="${h-50}" text-anchor="middle">${esc(fx.label||fx.name)}${fx.unit?' · '+esc(fx.unit):''}</text><text transform="translate(22 ${top+(h-top-bottom)/2}) rotate(-90)" text-anchor="middle">${esc(fy.label||fy.name)}</text><text class="axis-label" x="${left}" y="${h-13}">Green: stronger NOK than current scenario. Red: weaker NOK.</text></svg>`;
    $('scenario-surface').innerHTML=s;
  }
  function treasuryInputs() {
    const get=id=>Number($(id).value),amount=get('exposure-amount'),hedge=get('hedge-ratio')/100,reference=get('treasury-reference'),points=get('forward-points'),future=get('treasury-future'),type=$('exposure-type').value;
    if(![amount,hedge,reference,points,future].every(Number.isFinite)||amount<0||hedge<0||hedge>1||reference<=0||future<=0||reference+points<=0)return null;
    return {amount,hedge,reference,points,future,type,forward:reference+points,blended:hedge*(reference+points)+(1-hedge)*future};
  }
  function renderTreasury() {
    const t=treasuryInputs();if(!t){$empty('treasury-result','Enter a non-negative euro amount, a hedge ratio from 0% to 100% and positive exchange rates.');$empty('treasury-chart','Valid assumptions are required.');return;}
    const cash=t.amount*t.blended,ref=t.amount*t.reference,diff=cash-ref,favourable=t.type==='payable'?-diff:diff;
    const metrics=[[t.type==='payable'?'NOK cash paid':'NOK cash received',`NOK ${fmt(cash,0)}`,`Blended settlement rate ${fmt(t.blended,4)}`],['At the reference spot',`NOK ${fmt(ref,0)}`,`EUR ${fmt(t.amount,0)} × ${fmt(t.reference,4)}`],[t.type==='payable'?'Change in payment cost':'Change in receipts',`${diff>0?'+':''}NOK ${fmt(diff,0)}`,`${favourable>0?'Favourable':favourable<0?'Adverse':'Unchanged'} versus reference`]];
    $('treasury-result').innerHTML=metrics.map(([label,value,note],i)=>`<div class="kpi"><span>${esc(label)}</span><strong class="${i===2?tone(favourable):''}">${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
    const rows=Array.from({length:41},(_,i)=>{const spot=t.reference*(.8+i*.01);return{label:fmt(spot,2),unhedged:t.amount*spot/1000000,hedged:t.amount*(t.hedge*t.forward+(1-t.hedge)*spot)/1000000};});
    lineChart('treasury-chart',rows,[{key:'unhedged',label:'Unhedged NOK cash flow, millions',color:'var(--muted)',width:1.7},{key:'hedged',label:'Selected hedge NOK cash flow, millions',color:'var(--gold)',width:2.5}],'NOK cash flow in millions across settlement exchange rates');
    const n=document.createElement('p');n.className='small';n.textContent='Vertical axis: NOK millions. Horizontal axis: settlement EUR/NOK.';$('treasury-chart').appendChild(n);
  }
  function renderData() {
    const meta=state.results.metadata||{},sources=state.results.sources||[],coverage=state.results.data_coverage||[];
    $('data-summary').innerHTML=[['Target',meta.target_definition||'Cumulative log change in EUR/NOK at the selected forecast horizon.'],['Common information set',`${meta.core_series||coverage.length} observed series; ${meta.feature_count_full||'—'} features in the full model. The common feature panel starts ${meta.feature_sample_start||meta.sample_start||'—'}.`],['Chronology',`${meta.validation_label||'Historical walk-forward evaluation'}. ${meta.forecast_timestamp_warning||''} First prospective origin after protocol freeze: ${meta.first_prospective_origin||'not specified'}.`]].map(([label,text])=>`<div><h3>${esc(label)}</h3><p>${esc(text)}</p></div>`).join('');
    const mapping={spot_eurnok:['fx','EUR/NOK month-end fixing'],nb_policy:['nb','Norway policy rate'],ecb_dfr:['ecb','ECB deposit facility rate'],ecb_mro:['ecb','ECB main refinancing rate'],brent:['brent','Brent crude oil'],vix:['vix','VIX'],usd_broad:['usd','Broad U.S. dollar index'],no_hicp_yoy:['no_hicp_yoy','Norway HICP inflation'],ea_hicp_yoy:['ea_hicp_yoy','Euro area HICP inflation'],no_ip_yoy:['no_ip_yoy','Norway industrial production growth'],ea_ip_yoy:['ea_ip_yoy','Euro area industrial production growth']};
    const rows=coverage.map(c=>{const pair=mapping[c.series]||[c.series,c.series],source=sources.find(s=>s.id===pair[0])||{};return{...c,source,label:pair[1]};});
    if(!rows.length)$empty('source-table','Series coverage has not been supplied with this result snapshot.');
    else $('source-table').innerHTML=`<table><thead><tr><th>Input / series</th><th>Source</th><th>Retained coverage</th><th>Availability assumption</th><th>Provenance</th></tr></thead><tbody>${rows.map(r=>{const source=r.source,url=safeUrl(source.url||''),provider=/eurostat/.test(url)?'Eurostat':source.label||'—',series=Array.isArray(source.series)?source.series.join(' · '):source.series||r.series,lag=r.lag_months===0?'Current month-end observation / effective rate':`${r.lag_months}-month lag in model features`;return`<tr><td>${esc(r.label)}<small class="metric-note">${esc(series)}</small></td><td>${esc(provider)}</td><td>${esc(r.start||'—')} – ${esc(r.end||'—')}<span class="metric-note">${esc(r.count??'—')} observed months; ${esc(r.missing??'—')} missing in full panel</span></td><td>${esc(lag)}</td><td>${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Official source</a>`:'See retained manifest'}${source.retrieved_utc?`<span class="metric-note">Retrieved ${esc(source.retrieved_utc)}</span>`:''}</td></tr>`;}).join('')}</tbody></table>`;
    const extensions=sources.filter(s=>['ea_mpd','norway_surprises'].includes(s.id));
    $('extension-status').innerHTML=`<strong>Expectations and causal identification:</strong>${extensions.length?extensions.map(s=>`<p>${safeUrl(s.url)?`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.label)}</a>`:esc(s.label)} — ${esc(s.status||'Status not supplied')}.</p>`).join(''):' No surprise or expectations dataset is inferred from policy-rate changes.'}`;
    const limits=state.results.limitations||[];$('limitations').innerHTML=limits.length?limits.map(x=>`<li>${esc(typeof x==='string'?x:x?.text||x?.label||JSON.stringify(x))}</li>`).join(''):'<li>Consult the full methodology and retained source manifests before interpreting these results.</li>';
  }
  function renderEvents() {
    const data=state.eventStudy;
    if(!data){$empty('event-chart','The separate event-study artifact could not be loaded. No event effect is inferred.');return;}
    const rows=data.results||[],coverage=data.coverage||{},first=rows[0]||{};
    $('event-summary').innerHTML=[['Matched ECB events',first.n??'—',`${first.first_event||'—'} to ${first.last_event||'—'}`],['Observed repricing range',`${fmt(first.predictor_min_bp,1)} to ${fmt(first.predictor_max_bp,1)}`, 'Basis points, one-year OIS'],['Reported scale','+10 bp','A coefficient normalization, not a policy-rate hike'],['ECB dataset cutoff',coverage.ecb_last_event||'—','Excluded from current monthly model']].map(([label,value,note])=>`<div class="kpi"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
    const scaled=rows.map(r=>({...r,value:finite(r.coefficient_pct_per_10bp)?r.coefficient_pct_per_10bp:r.coefficient_pct_per_25bp*.4,ci:(r.block_bootstrap_ci95_per_10bp||r.block_bootstrap_ci95.map(v=>v*.4)),label:`${r.horizon_business_days} subsequent fixing${r.horizon_business_days===1?'':'s'}`}));
    ciChart('event-chart',scaled,'ECB event OIS repricing association per 10 basis points');
    $('event-table').innerHTML=`<table><thead><tr><th>Fixings after event</th><th class="number">Events</th><th class="number">Log-return association per +10 bp</th><th class="number">Nominal 95% block interval</th><th class="number">Bonferroni interval, 98.333% each</th><th class="number">R²</th><th class="number">Adjacent windows overlapping</th></tr></thead><tbody>${scaled.map(r=>`<tr><td>${esc(r.horizon_business_days)} business-day fixing${r.horizon_business_days===1?'':'s'}</td><td class="number">${esc(r.n)}</td><td class="number">${signed(r.value,3)}%</td><td class="number">${r.ci.map(v=>fmt(v,3)).join(' to ')}%</td><td class="number">${Array.isArray(r.bonferroni_ci98_333_per_10bp)?r.bonferroni_ci98_333_per_10bp.map(v=>fmt(v,3)).join(' to ')+'%':'Not supplied'}</td><td class="number">${fmt(r.r2,3)}</td><td class="number">${esc(r.adjacent_outcome_window_overlap_count??'—')}</td></tr>`).join('')}</tbody></table>`;
    const positive=scaled.filter(r=>r.ci[0]>0).map(r=>r.horizon_business_days);
    const adjusted=scaled.every(r=>Array.isArray(r.bonferroni_ci98_333_per_10bp));
    const survives=scaled.some(r=>Array.isArray(r.bonferroni_ci98_333_per_10bp)&&r.bonferroni_ci98_333_per_10bp[0]>0);
    $('event-reading').innerHTML=`<strong>${adjusted&&!survives?'No validated event signal after multiplicity adjustment.':'Exploratory event association.'}</strong> ${positive.length?`The nominal interval excludes zero at ${positive.map(x=>`${x}-fixing`).join(', ')} horizon${positive.length===1?'':'s'}. `:'No reported nominal interval excludes zero on the positive side. '}${adjusted?'The three-horizon Bonferroni intervals use 98.333% coverage for each comparison; '+(survives?'a positive interval remains.':'all adjusted intervals include zero.'):'Family-wise adjusted intervals have not been supplied.'} The repricing proxy contains policy, guidance and information effects, while other news can affect subsequent fixings. This does not establish a causal mechanism or a trading advantage.`;
    $('event-limitations').innerHTML=(data.limitations||[]).map(t=>`<li>${esc(t)}</li>`).join('');
    $('event-sources').innerHTML=(data.sources||[]).map(s=>`<p>${safeUrl(s.source_page||s.url)?`<a href="${esc(s.source_page||s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.publisher)}</a>`:esc(s.publisher)}${s.retrieved_utc?` · retrieved ${esc(s.retrieved_utc)}`:''}</p>`).join('');
  }
  function renderAll() { renderKpis();renderEvidence();renderDrivers();renderPath();renderScenarioControls();renderTreasury(); }
  function updateHorizon(value) {
    state.horizon=value;const models=hdata().models||[];
    if(!models.some(m=>m.id===state.model))state.model=models.find(m=>m.id==='rw')?.id||models[0]?.id||'';
    $('model-select').innerHTML=models.map(m=>`<option value="${esc(m.id)}">${esc(m.label)}</option>`).join('');$('model-select').value=state.model;renderAll();
  }
  function attachEvents() {
    document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>showTab(button.dataset.tab)));
    document.querySelector('.tabs').addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;const tabs=[...document.querySelectorAll('[data-tab]')],current=tabs.indexOf(document.activeElement);if(current<0)return;event.preventDefault();const at=event.key==='Home'?0:event.key==='End'?tabs.length-1:(current+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;showTab(tabs[at].dataset.tab,true);});
    document.querySelectorAll('[data-open-tab]').forEach(a=>a.addEventListener('click',event=>{event.preventDefault();showTab(a.dataset.openTab);$(`tab-${a.dataset.openTab}`).scrollIntoView({block:'center',behavior:'smooth'});}));
    document.querySelectorAll('[name=horizon]').forEach(input=>input.addEventListener('change',()=>updateHorizon(input.value)));
    $('model-select').addEventListener('change',()=>{state.model=$('model-select').value;renderAll();});
    $('surface-x').addEventListener('change',renderSurface);$('surface-y').addEventListener('change',renderSurface);
    $('reset-scenario').addEventListener('click',()=>{delete state.scenarioInputs[state.horizon];renderScenarioControls();});
    $('export-scenario').addEventListener('click',()=>download(`eurnok-scenario-${state.horizon}m.json`,{type:'conditional model scenario; not a causal shock',research_as_of:state.results?.metadata?.as_of,horizon_months:Number(state.horizon),model_id:hdata().scenario?.model_id,inputs:state.scenarioInputs[state.horizon],result:scenarioValue()}));
    $('use-scenario-treasury').addEventListener('click',()=>{if(finite(state.scenarioSpot)){$('treasury-future').value=state.scenarioSpot.toFixed(4);showTab('treasury');$('tab-treasury').focus();}});
    ['exposure-type','exposure-amount','hedge-ratio','treasury-reference','forward-points','treasury-future'].forEach(id=>$(id).addEventListener('input',renderTreasury));
    $('export-treasury').addEventListener('click',()=>{const t=treasuryInputs();if(t)download('eurnok-treasury-scenario.json',{type:'user-defined cash-flow scenario; no hedge recommendation',...t,settlement_cash_nok:t.amount*t.blended,reference_cash_nok:t.amount*t.reference,excluded:['Fees','Collateral','Counterparty risk','Early termination','Hedge accounting']});});
    $('export-results').addEventListener('click',()=>download(`eurnok-comparison-${state.horizon}m.csv`,csv([['horizon_months','model','mae_pp','rmse_pp','direction_accuracy','gain_vs_random_walk_pp','ci_95_lower','ci_95_upper','observations'],...(hdata().models||[]).map(m=>[state.horizon,m.label,m.mae,m.rmse,m.direction_accuracy,m.improvement_vs_rw,m.improvement_ci?.[0],m.improvement_ci?.[1],m.n])]),'text/csv;charset=utf-8'));
  }
  async function init() {
    document.body.classList.add('loading');attachEvents();
    try {
      const r=await fetch('model/output/results.json',{cache:'no-store'});if(!r.ok)throw new Error(`Research results returned HTTP ${r.status}.`);
      state.results=await r.json();if(!state.results.horizons||!Object.keys(state.results.horizons).length)throw new Error('The result snapshot does not contain a horizon panel.');
      try{const p=await fetch('model/output/predictions.json',{cache:'no-store'});if(p.ok)state.predictions=await p.json();}catch{/* Evidence remains usable when prediction history is unavailable. */}
      try{const e=await fetch('model/output/event_study.json',{cache:'no-store'});if(e.ok)state.eventStudy=await e.json();}catch{/* Historical event analysis is a separate, optional module. */}
      const horizons=Object.keys(state.results.horizons);state.horizon=horizons.includes('1')?'1':horizons[0];
      document.querySelectorAll('[name=horizon]').forEach(input=>{input.disabled=!horizons.includes(input.value);input.checked=input.value===state.horizon;});
      $('model-select').disabled=false;$('export-results').disabled=false;metadata();updateHorizon(state.horizon);renderData();renderEvents();
      if(location.hash==='#data')showTab('data');
    }catch(error){$('load-error').classList.remove('hidden');$('load-error').textContent=`The retained result snapshot could not be loaded. ${error.message} Open this page through the published website or a local HTTP server; the source files and methodology remain available.`;$('research-status').innerHTML='<strong>Evidence unavailable</strong><span>No model scores or forecasts are inferred when the result file is missing.</span>';}
    finally{document.body.classList.remove('loading');}
  }
  init();
})();
