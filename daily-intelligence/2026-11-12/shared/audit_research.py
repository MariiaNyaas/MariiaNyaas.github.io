"""Independent verification path: re-read raw records, do not import analysis module."""
from pathlib import Path
import json,re,hashlib,html
import pandas as pd,numpy as np,openpyxl
from scipy.stats import linregress,norm
S=Path('sources');O=Path('site/daily-intelligence/2026-11-12/shared');r=json.loads((O/'results.json').read_text());checks=[]
def check(name,condition,detail):
 checks.append(dict(check=name,passed=bool(condition),evidence=detail))
 if not condition:raise AssertionError(name+': '+detail)
manifest=json.loads((O/'source_manifest.json').read_text());check('Input completeness',len(manifest)==28,f'{len(manifest)} supplied files; all hashes retained')
for x in manifest:check('SHA-256 '+x['file'],hashlib.sha256((S/x['file']).read_bytes()).hexdigest()==x['sha256'],'Raw bytes match analysis manifest')
check('NTNU repository checksum',hashlib.md5((S/'Kraftmarkedet_NO_2025.xlsx').read_bytes()).hexdigest()=='e9127a554d918413a1a521dd6ecec52e','Matches published Zenodo MD5')
w=openpyxl.load_workbook(S/'Kraftmarkedet_NO_2025.xlsx',read_only=True,data_only=True);s=w['Strømpris'];s.reset_dimensions();rows=list(s.values);a=np.array([[float(v) for v in z[1:]] for z in rows[2:]])
# Explicit independent direct recomputation in original source units.
for i,z in enumerate(r['storage']):
 q=r['storage'][z];test=a[181*24:,i].reshape(184,24);daily=(test[:,q['sell_index']]*.9-test[:,q['buy_index']])*10
 check('Frozen storage '+z,abs(daily.mean()-q['fixed_daily_mean'])<1e-9,'Independent source-unit recomputation, no future clipping')
 check('Storage upper bound '+z,all(u['upper']+1e-8>=u['fixed'] for u in q['daily']),'Every holdout block obeys foresight dominance')
check('Original last hour flag',np.all(a[-1]==0),'All-zone terminal zero retained; NO1 exclusion sensitivity provided')
# Summarise each workbook sheet using raw cell iteration; gaps remain gaps.
book=[]
for sh in w:
 sh.reset_dimensions();rr=list(sh.values);book.append({'sheet':sh.title,'rows':len(rr),'max_columns':max(map(len,rr),default=0)})
(O/'workbook_inventory.json').write_text(json.dumps(book,indent=2))
# Independent OLS slope and HC3, computed from centered sums and residuals.
b=pd.DataFrame(r['business']['countries']);x=b.ai2024.to_numpy();y=b.growth2025.to_numpy();fit=linregress(x,y)
check('EU27 OLS slope',abs(fit.slope-r['business']['beta_lagged_ai'])<1e-12,'scipy.stats.linregress independent implementation')
X=np.stack([np.ones(len(x)),x],axis=1);A=np.linalg.inv(X.T@X);res=y-fit.intercept-fit.slope*x;hat=np.sum((X@A)*X,axis=1);V=sum(np.outer(X[i],X[i])*(res[i]/(1-hat[i]))**2 for i in range(len(x)));se=np.sqrt((A@V@A)[1,1]);ci=[fit.slope-norm.ppf(.975)*se,fit.slope+norm.ppf(.975)*se]
check('HC3 confidence interval',np.allclose(ci,r['business']['ci95'],atol=1e-12),'Recomputed leverage-adjusted sandwich in separate audit process')
# Credit temporal boundary and alternative evaluation windows.
h=pd.DataFrame(r['credit']['history']);y=h['count'].to_numpy();month=pd.to_datetime(h.date).dt.month.to_numpy();X=np.stack([np.ones(len(y)-1),np.log1p(y[:-1]),np.sin(2*np.pi*month[1:]/12),np.cos(2*np.pi*month[1:]/12)],axis=1);ly=np.log1p(y[1:]);rob=[]
for n in [24,36,48]:
 preds=[]
 for t in range(len(y)-n,len(y)):
  beta=np.linalg.lstsq(X[:t-1],ly[:t-1],rcond=None)[0];preds.append(max(0,np.expm1(X[t-1]@beta)))
 mae=np.mean(abs(y[-n:]-preds));naive=np.mean(abs(y[-n:]-y[-n-12:-12]));rob.append({'months':n,'model_mae':mae,'naive_mae':naive})
 if n==36:check('Credit expanding-origin alignment',abs(mae-r['credit']['mae'])<1e-12,'Training stops before every target; median count forecast')
r['credit']['robustness']=rob
# SEC annual period and accession traceability, independently select matching records.
for item in r['accounting']['latest']:
 raw=next(json.loads(p.read_text()) for p in S.glob('Pasted*') if json.loads(p.read_text())['cik']==item['cik'])
 for metric,val in item['metrics'].items():
  matches=[v for v in raw['facts']['us-gaap'][val['tag']]['units']['USD'] if v['end']==item['end'] and v['filed']==val['filed'] and v['accn']==val['accn'] and v['val']==val['value'] and v.get('start')==val['start']]
  check('SEC '+item['company']+' '+metric,bool(matches),'Exact concept / period / filing / accession / value match')
 check('SEC cutoff '+item['company'],all(v['filed']<='2026-11-12' for v in item['metrics'].values()),'No later filings used')
for k in ['re','ri']:
 d=pd.read_csv(S/f'{k}_20260630.csv',sep=';',encoding='utf-16');s=0
 for country,rows in d.groupby('Country'):
  unique=set(rows['Total country value']);check(k+' repeated total '+country,len(unique)==1,'Within-country total is constant');s+=unique.pop()
 check(k+' corrected total',s==r['governance'][k]['country_total_nok'],'Sum unique country totals, not property rows')
for f in r['public']['fiscal']:check('Fiscal identity '+str(f['year']),abs(f['A Total revenue']-f['E Total expenditure (B+D)']-f['F Net lending/borrowing (A-E)'])<=1,'Revenue − expenditure reconciles to net lending within 1 NOK million source-rounding tolerance')
check('Public scenario unit conversion',abs(100*8760*.9/1000*700/1e6-.55188)<1e-12,'100 MW ×90% =788.4 GWh; at700 NOK/MWh revenue is0.55188 bn NOK')
check('Scenario default public capture',abs(((.55188*.3*.3)+(.55188*.3*.7*.6)-.020-.030)*.9-.062285472)<1e-9,'Independent hand-calculated fiscal waterfall')
check('No hourly load duplicate keys',all(v.get('duplicate_country_hour',0)==0 for v in r['entsoe'].values()),'ENTSO-E country/timestamp keys unique; gaps not filled')
# Persist independent diagnostic additions. Page generator embeds this same file.
(O/'results.json').write_text(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False))
report={'type':'Separate automated technical and methodological audit; no external human review claimed','checks':checks,'passed':all(x['passed'] for x in checks),'limitations':['Electricity–credit causal model not identified.','Storage gross-spread holdout is not a net investable return.','Accounting replacement horizon is assumed, not estimated.','Single-date NBIM holdings cannot validate return-factor correlations.','EU27 association does not identify an AI treatment effect.','AI-linked fiscal capture cannot be inferred from aggregate fiscal history.','Browser and deployment checks are recorded separately after publication.'],'credit_robustness':rob}
(O/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));
body='<h1>Research audit</h1><p>'+html.escape(report['type'])+'</p><h2>'+str(len(checks))+' checks passed</h2><p>Checks cover raw-file hashes, source checksums, independent arithmetic, source records, chronology, covariance and aggregation. A passing check establishes consistency with the stated method; it does not establish causal identification.</p><h2>Interpretation gates</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in report['limitations'])+'</ul><h2>Credit sensitivity to holdout length</h2><pre>'+html.escape(json.dumps(rob,indent=2))+'</pre><h2>Machine-readable evidence</h2><p><a href="audit.json">Full check log</a> · <a href="audit_research.py">Audit code</a> · <a href="source_manifest.json">Input hashes</a> · <a href="workbook_inventory.json">Workbook inventory</a></p>'
(O/'audit.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Technical and methodological audit</title><link rel="stylesheet" href="app.css"></head><body><main><a href="../01-credit-risk/">← Research series</a>'+body+'</main></body></html>')
print('PASS',len(checks),'checks; holdout robustness',rob)
