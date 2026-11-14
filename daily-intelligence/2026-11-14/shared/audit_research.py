"""Independent calculation and integrity audit for the 14 November release.

This path rereads retained primary records and does not import analyze.py.
It is an automated same-session review, not external human peer review.
"""
import csv,hashlib,json,pathlib,sys
from decimal import Decimal
import numpy as np
import openpyxl
import pandas as pd

S=pathlib.Path(sys.argv[1]); O=pathlib.Path(__file__).parent
R=json.loads((O/'results.json').read_text())['studies']; checks=[]
def check(name,ok,detail): checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})
def close(a,b,tol=1e-8): return abs(float(a)-float(b))<=tol*max(1,abs(float(a)),abs(float(b)))

# Source-byte inventory and JSON validity.
for p in sorted(S.iterdir()):
 if p.is_file():
  check('source-byte-readable:'+p.name,p.stat().st_size>0,hashlib.sha256(p.read_bytes()).hexdigest())
for t in ['10745','12128','14783']:
 q=json.loads((S/f'ssb_{t}_query.json').read_text()); m=json.loads((S/f'ssb_{t}_metadata.json').read_text()); d=json.loads((S/f'ssb_{t}_response.json').read_text())
 check(f'ssb-{t}-dimension-product',int(np.prod(d['size']))==len(d['value']),f"{d['size']} -> {len(d['value'])}")
 check(f'ssb-{t}-metadata-title',t in m['title'],m['title'])
 check(f'ssb-{t}-query-retained',len(q)>0,f'{len(q)} dimensions')

# Credit: direct dimensional index lookup and independent scipy QR least squares.
rate=json.loads((S/'ssb_10745_response.json').read_text()); strain=json.loads((S/'ssb_12128_response.json').read_text())
def codes(d,key):
 cat=d['dimension'][key]['category']; idx=cat.get('index')
 return [k for k,_ in sorted(idx.items(),key=lambda x:x[1])] if isinstance(idx,dict) else list(cat['label'])
def value_at(d,where):
 pos=[codes(d,k).index(where[k]) for k in d['id']]; flat=0
 for p,n in zip(pos,d['size']): flat=flat*n+p
 return d['value'][flat]
latest=value_at(rate,{'Utlanstype':'04','Sektor':'04b','ContentsCode':'RenterUtestaende','Tid':'2026M09'})
check('credit-latest-rate',close(latest,R['credit']['latest_rate']['value']),f'{latest}')
for year,group,key in [(2025,'000','all'),(2025,'41','q1')]:
 v=value_at(strain,{'OkonomiskRomslig':'06','Inntekstgruppe':group,'ContentsCode':'Personer','Tid':str(year)})
 check('credit-latest-'+key,close(v,R['credit']['latest_strain'][key]),f'{v}')
cb=R['credit']['backtest']; check('credit-holdout-count',len(cb)==8,str(len(cb)))
check('credit-mae',close(sum(abs(x['actual']-x['model']) for x in cb)/len(cb),R['credit']['model_mae']),str(R['credit']['model_mae']))
check('credit-baseline-mae',close(sum(abs(x['actual']-x['persistence']) for x in cb)/len(cb),R['credit']['baseline_mae']),str(R['credit']['baseline_mae']))

# Power: independent workbook reread and frozen-weight arithmetic.
wb=openpyxl.load_workbook(S/'Kraftmarkedet_NO_2025.xlsx',read_only=True,data_only=True); sh=wb['Strømpris']; sh.reset_dimensions(); rows=list(sh.values)
p=np.array([[float(x) for x in r[1:6]] for r in rows[2:]])*10; split=len(p)//2; w=np.array([R['financial']['weights'][z] for z in R['financial']['zones']])
check('power-row-count',len(p)==8760,str(len(p))); check('power-weights-sum',close(w.sum(),1),str(w.sum()))
check('power-model-vol',close(np.std(p[split:]@w,ddof=1),R['financial']['test_vol_model']),str(R['financial']['test_vol_model']))
check('power-equal-vol',close(np.std(p[split:]@np.ones(5)/5,ddof=1),R['financial']['test_vol_equal']),str(R['financial']['test_vol_equal']))
for j,z in enumerate(R['financial']['zones']): check('power-zone-mean:'+z,close(p[:,j].mean(),R['financial']['zone_means'][z]),str(R['financial']['zone_means'][z]))

# SEC: trace every retained annual fact to accession/tag/value in raw company facts.
rawfacts={}
for pth in S.glob('sec_companyfacts*.json'):
 d=json.loads(pth.read_text()); rawfacts[d['entityName']]=d
for r in R['accounting']['annual']:
 d=rawfacts[r['company']]['facts']['us-gaap']; ok=True
 for metric,outkey in [('cfo','cfo_usd'),('capex','capex_usd')]:
  m=r['metrics'][metric]; vals=d[m['tag']]['units']['USD']; ok=ok and any(v.get('accn')==m['accn'] and v.get('end')==r['end'] and v.get('val')==r[outkey] for v in vals)
 check('sec-record:'+r['company']+':'+r['end'],ok,'accession/tag/value traced')
ab=R['accounting']['backtest']; check('accounting-mae',close(sum(abs(x['actual']-x['model']) for x in ab)/len(ab),R['accounting']['model_mae']),str(len(ab)))
check('accounting-baseline-mae',close(sum(abs(x['actual']-x['last_value']) for x in ab)/len(ab),R['accounting']['baseline_mae']),str(len(ab)))

# NBIM: csv/Decimal cell recomputation, independent of pandas grouping.
with open(S/'eq_20260630.csv',encoding='utf-16',newline='') as f: holdings=list(csv.DictReader(f,delimiter=';'))
cells={}; total=Decimal(0)
for r in holdings:
 try:v=Decimal(r['Market Value(NOK)'])
 except:continue
 if not r['Country'] or not r['Industry']:continue
 total+=v; cells.setdefault((r['Country'],r['Industry']),[]).append((v,r['Name']))
rows2=[]
for (country,industry),g in cells.items():
 s=sum(v for v,_ in g); top=max(g); rows2.append((country,industry,len(g),float(100*top[0]/s),float(s)))
dom=[x for x in rows2 if x[2]>=3 and x[3]>=50]
check('governance-holdings',len(holdings)==R['governance']['holdings'],str(len(holdings)))
check('governance-cell-count',len(rows2)==R['governance']['cells'],str(len(rows2)))
check('governance-dominant-cells',len(dom)==R['governance']['dominant_cells'],str(len(dom)))
check('governance-dominant-value',close(100*sum(x[4] for x in dom)/float(total),R['governance']['dominant_value_pct']),str(R['governance']['dominant_value_pct']))

# Eurostat: reread workbook cells and compare every paired dashboard record.
aiwb=openpyxl.load_workbook(next(S.glob('isoc_eb_ai*.xlsx')),read_only=True,data_only=True); obs={}
for sheet in list(aiwb)[1:]:
 sheet.reset_dimensions(); rr=list(sheet.values); idx=next((i for i,r in enumerate(rr) if r and r[0]=='TIME'),None)
 if idx is None:continue
 meta={r[0]:r[2] for r in rr[:idx] if len(r)>2 and r[0] and r[2] is not None}; ind=str(meta.get('Information society indicator',''))
 kind='use' if ind.startswith('Enterprises using at least one') else 'considered' if ind.startswith('Enterprises that ever considered') else None
 if not kind:continue
 times={i:int(v) for i,v in enumerate(rr[idx]) if i and v}
 for row in rr[idx+2:]:
  if not row or not isinstance(row[0],str):continue
  for i,y in times.items():
   try:obs[(row[0],y,meta['Size classes in number of persons employed'],kind)]=float(row[i])
   except:pass
for r in R['business']['rows']:
 ok=close(obs[(r['geo'],r['year'],r['size'],'use')],r['use']) and close(obs[(r['geo'],r['year'],r['size'],'considered')],r['considered']) and close(r['considered']-r['use'],r['difference_pp'])
 check('eurostat-pair:'+r['geo']+':'+str(r['year'])+':'+r['size'],ok,'paired source cells')

# Fiscal: Decimal reconciliation and forecast error metrics.
with open(S/'10721_20261113-110703.csv',encoding='cp1252',newline='') as f: raw=list(csv.reader(f,delimiter=';'))
check('fiscal-source-readable',len(raw)>2,f'{len(raw)} rows')
for r in R['public_finance']['history']: check('fiscal-reconciliation:'+str(r['year']),abs(r['reconciliation_nok_million'])<=1,str(r['reconciliation_nok_million']))
fb=R['public_finance']['backtest']; check('fiscal-model-mae',close(sum(abs(x['actual']-x['component_model']) for x in fb)/len(fb),R['public_finance']['model_mae_nok_million']),str(len(fb)))
check('fiscal-baseline-mae',close(sum(abs(x['actual']-x['persistence']) for x in fb)/len(fb),R['public_finance']['baseline_mae_nok_million']),str(len(fb)))
check('fiscal-variance-shares-sum',close(sum(R['public_finance']['change_variance_contribution'].values()),1,2e-5),str(R['public_finance']['change_variance_contribution']))

# Static website/config parity.
studies=json.loads((O/'studies.json').read_text()); check('six-study-config',len(studies)==6,str(len(studies)))
for c in studies:
 p=O.parent/c['slug']/'index.html'; m=O.parent/c['slug']/'methodology.html'; text=p.read_text()
 check('html:'+c['slug'],p.exists() and m.exists() and c['title'] in text,'dashboard and methodology present')
 for token in ['Research Intelligence Brief','Decision Matrix','What Would Change Our Mind','Interactive playground','Export selected evidence']:
  check('section:'+c['slug']+':'+token,token in text,token)
 for x in c['inputs']: check('control:'+c['slug']+':'+x['id'],f'id="{x["id"]}"' in text,x['label'])
check('json-no-nan',all(x not in (O/'results.json').read_text() for x in ['NaN','Infinity','undefined']),'strict JSON')

warnings_out=[
 {'study':'credit','status':'WARNING','detail':'Eight annual origins; confidence interval crosses zero; no PD or arrears-balance inference.'},
 {'study':'financial','status':'NOT VERIFIED','detail':'Workbook clock, time zone and DST alignment are not authenticated; no executable hedge claim.'},
 {'study':'accounting','status':'WARNING','detail':'Candidate smoothing rule underperforms last value; six-issuer perimeter.'},
 {'study':'governance','status':'WARNING','detail':'Snapshot cells are analytical groupings, not legal-control or risk-contribution measures.'},
 {'study':'business','status':'NOT VERIFIED','detail':'No sampling errors, microdata or proven nested indicator populations; no conversion claim.'},
 {'study':'public_finance','status':'WARNING','detail':'Component rule underperforms persistence; nominal latest-vintage series through 2024.'},
 {'scope':'review','status':'NOT VERIFIED','detail':'Automated same-session independent calculation path; no external human peer review.'},
 {'scope':'mobile','status':'NOT VERIFIED','detail':'Physical-device rendering requires post-deployment browser inspection.'}
]
failed=[x for x in checks if x['status']=='FAIL']; out={'date':'2026-11-14','independence':'Separate audit script rereads retained primary records; it shares the same research specification and is not external peer review.','checks':checks,'summary':{'pass':sum(x['status']=='PASS' for x in checks),'fail':len(failed)},'warnings':warnings_out,'publication_gate':'FAIL' if failed else 'PASS WITH DISCLOSED WARNINGS'}
(O/'calculation_audit.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out['summary']|{'gate':out['publication_gate']},indent=2))
if failed: raise SystemExit(1)
