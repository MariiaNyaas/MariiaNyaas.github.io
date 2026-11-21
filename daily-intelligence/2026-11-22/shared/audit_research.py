#!/usr/bin/env python3
"""Independent source-record and score audit for the 22 November 2026 release."""
from __future__ import annotations
import hashlib,json,math,pathlib,re,sys
import numpy as np
import pandas as pd

SOURCE=pathlib.Path(sys.argv[1]).resolve(); RELEASE=pathlib.Path(sys.argv[2]).resolve()
RESULT=json.loads((RELEASE/'shared/results.json').read_text()); STUDIES=json.loads((RELEASE/'shared/studies.json').read_text())
checks=[]
def check(name,condition,detail=''):
 checks.append({'name':name,'status':'PASS' if condition else 'FAIL','detail':str(detail)})
def close(a,b,tol=1e-7): return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=tol*max(1,abs(float(a)),abs(float(b)))
def rows(path):
 d=json.loads(path.read_text()); ids,sizes=d['id'],d['size']; cats=[]
 for key in ids:
  c=d['dimension'][key]['category']; order=c.get('index',{}); codes=[k for k,_ in sorted(order.items(),key=lambda p:p[1])] if isinstance(order,dict) else list(c.get('label',{})); cats.append(codes)
 raw=d.get('value',{}); vals={int(k):v for k,v in raw.items()} if isinstance(raw,dict) else dict(enumerate(raw)); out=[]
 for flat,value in vals.items():
  rem=flat;coord=[0]*len(sizes)
  for j in range(len(sizes)-1,-1,-1): coord[j],rem=rem%sizes[j],rem//sizes[j]
  row={ids[j]:cats[j][coord[j]] for j in range(len(ids))};row['value']=value;out.append(row)
 return out

check('Exactly seven studies',len(STUDIES)==7,len(STUDIES))
check('Exactly seven result objects',len(RESULT['studies'])==7,len(RESULT['studies']))
manifest={x['file']:x for x in json.loads((RELEASE/'shared/extraction_manifest.json').read_text())}
for name,record in manifest.items():
 p=SOURCE/name;check('Source exists: '+name,p.exists())
 if p.exists():
  check('Source byte size: '+name,p.stat().st_size==record['bytes'],p.stat().st_size)
  check('Source SHA-256: '+name,hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'])

# Credit source reread and latest aggregate.
burden=pd.DataFrame(rows(SOURCE/'ssb_08727_response.json'));burden['value']=pd.to_numeric(burden.value);burden['year']=burden.Tid.astype(int)
latest=burden[(burden.year==burden.year.max())&(burden.Hushaldstype=='50')].value.sum()
check('Credit latest ≥15% burden recomputed',close(latest,RESULT['studies']['credit']['latest_burden']),latest)
credit_bt=RESULT['studies']['credit']['backtest'];check('Credit model MAE rescored',close(np.mean([abs(x['actual']-x['model']) for x in credit_bt]),RESULT['studies']['credit']['model_mae']))
check('Credit baseline MAE rescored',close(np.mean([abs(x['actual']-x['persistence']) for x in credit_bt]),RESULT['studies']['credit']['baseline_mae']))

# Financial raw reread.
fx=pd.read_csv(SOURCE/'norges_eurnok_monthly.csv',sep=';');rates=pd.read_csv(SOURCE/'norges_policy_rate.csv',sep=';');sd=rates[rates.TENOR=='SD'].copy();sd['date']=pd.to_datetime(sd.TIME_PERIOD);last_month=fx.TIME_PERIOD.iloc[-1]
check('Financial latest month reread',last_month==RESULT['studies']['financial']['latest']['date'],last_month)
check('Financial latest EUR/NOK reread',close(fx.OBS_VALUE.iloc[-1],RESULT['studies']['financial']['latest']['eurnok']),fx.OBS_VALUE.iloc[-1])
financial_bt=RESULT['studies']['financial']['backtest'];check('Financial model MAE rescored',close(np.mean([abs(x['actual_return_pct']-x['model_return_pct']) for x in financial_bt]),RESULT['studies']['financial']['model_mae']))
check('Financial baseline MAE rescored',close(np.mean([abs(x['actual_return_pct']) for x in financial_bt]),RESULT['studies']['financial']['baseline_mae']))

# Accounting accession/value traceability against primary SEC records.
raw_facts={}
for path in SOURCE.glob('sec_companyfacts_*.json'):
 d=json.loads(path.read_text());raw_facts[d['cik']]=d
for record in RESULT['studies']['accounting']['annual']:
 facts=raw_facts[record['cik']]['facts']['us-gaap']
 for metric in ['revenue','cfo','ar','inventory','ap']:
  m=record['metrics'][metric];values=facts[m['tag']]['units']['USD'];matched=any(x.get('accn')==m['accn'] and x.get('val')==m['value'] for x in values)
  check(f"SEC fact trace {record['company']} {record['end']} {metric}",matched,m['tag'])
 check(f"CFO margin formula {record['company']} {record['end']}",close(100*record['cfo_usd']/record['revenue_usd'],record['cfo_margin_pct']))
account_bt=RESULT['studies']['accounting']['backtest'];check('Accounting model MAE rescored',close(np.mean([abs(x['actual']-x['model']) for x in account_bt]),RESULT['studies']['accounting']['model_mae']))
check('Accounting baseline MAE rescored',close(np.mean([abs(x['actual']-x['persistence']) for x in account_bt]),RESULT['studies']['accounting']['baseline_mae']))

# Governance primary CSV reread.
hold=pd.read_csv(SOURCE/'nbim_equity_20260630.csv',sep=';',encoding='utf-16');hold['mv']=pd.to_numeric(hold['Market Value(NOK)'],errors='coerce')
for col in ['Voting','Ownership']: hold[col]=pd.to_numeric(hold[col].astype(str).str.replace('%','',regex=False),errors='coerce')
hold=hold.dropna(subset=['mv','Voting','Ownership']);gap=(hold.Voting-hold.Ownership).abs();weighted=float(np.average(gap,weights=hold.mv))
check('Governance holdings count reread',len(hold)==RESULT['studies']['governance']['holdings'],len(hold))
check('Governance weighted absolute gap recomputed',close(weighted,RESULT['studies']['governance']['weighted_abs_gap_pp']),weighted)

# Business source values and leave-one-out score reread.
business=RESULT['studies']['business'];norway=next(x for x in business['history'] if x['country_code']=='NO')
check('Business Norway 2024 AI source value',close(norway['ai_use_2024_pct'],20.77),norway['ai_use_2024_pct'])
check('Business Norway 2025 AI source value',close(norway['ai_use_2025_pct'],28.89),norway['ai_use_2025_pct'])
check('Business model MAE rescored',close(np.mean([abs(x['actual']-x['model']) for x in business['backtest']]),business['model_mae']))
check('Business baseline MAE rescored',close(np.mean([abs(x['actual']-x['persistence']) for x in business['backtest']]),business['baseline_mae']))

# Public-finance source reread.
fiscal=pd.DataFrame(rows(SOURCE/'ssb_10721_response.json'));fiscal['value']=pd.to_numeric(fiscal.value);fiscal['year']=fiscal.Tid.astype(int);latest_year=fiscal.year.max();inc=float(fiscal[(fiscal.year==latest_year)&(fiscal.Sektor=='C_OFF')&(fiscal.Art=='A51')].value.iloc[0]);exp=float(fiscal[(fiscal.year==latest_year)&(fiscal.Sektor=='C_OFF')&(fiscal.Art=='B41')].value.iloc[0]);public=RESULT['studies']['public_finance']
check('Public interest income reread',close(inc,public['latest']['interest_income_nok_million']),inc)
check('Public interest expense reread',close(exp,public['latest']['interest_expense_nok_million']),exp)
check('Public net-interest identity',close(inc-exp,public['latest']['net_interest_nok_million']),inc-exp)
check('Public model MAE rescored',close(np.mean([abs(x['actual']-x['model']) for x in public['backtest']]),public['model_mae_nok_million']))
check('Public baseline MAE rescored',close(np.mean([abs(x['actual']-x['persistence']) for x in public['backtest']]),public['baseline_mae_nok_million']))

# Art source reread and no double count.
vis=pd.DataFrame(rows(SOURCE/'ssb_09539_response.json'));vis['value']=pd.to_numeric(vis.value);vis['year']=vis.Tid.astype(int);fin=pd.DataFrame(rows(SOURCE/'ssb_09542_response.json'));fin['value']=pd.to_numeric(fin.value);fin['year']=fin.Tid.astype(int);y=min(vis.year.max(),fin.year.max());individual=float(vis[(vis.year==y)&(vis.MuseBesok=='01')].value.iloc[0]);group=float(vis[(vis.year==y)&(vis.MuseBesok=='02')].value.iloc[0]);rev=float(fin[(fin.year==y)&(fin.ContentsCode=='Inntekter')].value.iloc[0]);pub=float(fin[(fin.year==y)&(fin.ContentsCode=='Loyvingar')].value.iloc[0]);art=RESULT['studies']['art']
check('Art total visits independent sum',close(individual+group,art['latest']['total_visits']),individual+group)
check('Art subsidy share independent formula',close(100*pub/rev,art['latest']['subsidy_share_pct']),100*pub/rev)
check('Art model MAE rescored',close(np.mean([abs(x['actual']-x['model']) for x in art['backtest']]),art['model_mae_visits']))
check('Art baseline MAE rescored',close(np.mean([abs(x['actual']-x['persistence']) for x in art['backtest']]),art['baseline_mae_visits']))

# Static dashboard and methodology contract.
required=['Research Intelligence Brief','Decision Matrix','What Would Change Our Mind','Interactive playground','Sources &amp; reproducibility']
for study in STUDIES:
 page=RELEASE/study['slug']/'index.html';method=RELEASE/study['slug']/'methodology.html';check('Dashboard exists: '+study['slug'],page.exists());check('Methodology exists: '+study['slug'],method.exists())
 text=page.read_text();
 for phrase in required: check(f"{study['slug']} section: {phrase}",phrase in text)
 for inp in study['inputs']: check(f"{study['slug']} control: {inp['id']}",f'id="{inp["id"]}"' in text)
 check(study['slug']+' explicit scenario classification','USER SCENARIO — NOT AN EMPIRICAL RESULT' in text)
 check(study['slug']+' no placeholders',not re.search(r'\b(?:NaN|undefined|TODO)\b|Lorem ipsum',text,re.I))

check('JSON contains no NaN/Infinity',not re.search(r'\b(?:NaN|Infinity|-Infinity)\b',(RELEASE/'shared/results.json').read_text()))
check('Research catalog contains seven release URLs',sum('/daily-intelligence/2026-11-22/' in x.get('url','') for x in json.loads((RELEASE.parents[1]/'research.json').read_text()))==7)
failed=[x for x in checks if x['status']=='FAIL'];report={'date':'2026-11-22','classification':'same-session automated independent source-record and score audit; not external human peer review','checks':checks,'pass':len(checks)-len(failed),'fail':len(failed),'status':'PASS' if not failed else 'FAIL'}
(RELEASE/'shared/calculation_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'pass':report['pass'],'fail':report['fail'],'status':report['status']},indent=2))
sys.exit(1 if failed else 0)
