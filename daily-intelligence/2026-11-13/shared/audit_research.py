"""Second calculation path. Run beside release files; no network.
Uses raw gzip sources, csv+Decimal and scipy QR least squares rather than importing analyze.py.
"""
import json,pathlib,gzip,hashlib,csv,io,re,sys,platform
from decimal import Decimal as Dec
import numpy as np,openpyxl
from scipy.linalg import lstsq
P=pathlib.Path(__file__).parent;R=json.loads((P/'results.json').read_text())['studies'];checks=[];raw={}
def chk(name,condition,scope):
 checks.append({'check':name,'status':'PASS' if bool(condition) else 'FAIL','scope':scope})
 if not condition:raise AssertionError(name)
for a in json.loads((P/'source_manifest.json').read_text()):
 data=gzip.decompress((P/'sources'/a['download']).read_bytes());raw[a['file']]=data;chk('SHA256 '+a['file'],hashlib.sha256(data).hexdigest()==a['sha256'],'Original uncompressed bytes')
def file(prefix):return next(v for k,v in raw.items() if k.startswith(prefix))
def csvrows(data,enc,skip=False):
 text=data.decode(enc);text=text.split('\n',1)[1] if skip else text
 return list(csv.DictReader(io.StringIO(text),delimiter=';'))
# Independent primary row selection and QR fit, all held-out targets.
b=csvrows(file('08551'),'cp1252',True);pairs=[]
for k,v in b[0].items():
 m=re.fullmatch(r'Bankruptcies (\d{4})M(\d{2}) 03 Oslo - Oslove',k)
 if m:pairs.append((f'{m[1]}-{m[2]}',float(v)))
pairs.sort();y=[p[1] for p in pairs];features=[];targets=[]
for t in range(24,len(y)-2):
 features.append([1,y[t-1],sum(y[t-12:t])/12,sum(y[t-3:t]),np.sin(2*np.pi*t/12),np.cos(2*np.pi*t/12)]);targets.append(sum(y[t:t+3]))
for j,row in enumerate(R['credit']['backtest'],start=len(targets)-36):
 t=24+j;coef=lstsq(np.array(features[:j-2]),np.array(targets[:j-2]),lapack_driver='gelsy')[0];pred=max(0,np.dot(features[j],coef));chk('Credit origin '+row['date'],abs(pred-row['model'])<1e-7 and sum(y[t:t+3])==row['actual'] and sum(y[t-12:t-9])==row['seasonal_naive'],'QR solver; last training target ends before forecast origin; actual source labels')
chk('Credit uncertainty crosses zero',R['credit']['mae_improvement_ci_blocks']['6'][0]<0<R['credit']['mae_improvement_ci_blocks']['6'][1],'No validated-superiority claim')
# SEC all selected periods, source records and same flow duration.
for row in R['accounting']['annual']:
 d=json.loads(file('sec_companyfacts_'+str(row['cik']).zfill(10)));m=row['metrics'];vals={}
 for name in ['cfo','capex']:
  v=m[name];hits=[x for x in d['facts']['us-gaap'][v['tag']]['units']['USD'] if all(x.get(k)==v[k] for k in ['start','end','filed','accn'])];assert hits and all(x['val']==v['value'] for x in hits);assert v['filed']<='2026-11-13';vals[name]=Dec(str(v['value']))
 chk('SEC '+row['company']+' '+row['end'],Dec(str(row['cash_after_capex_usd']))==vals['cfo']-vals['capex'] and m['cfo']['start']==m['capex']['start'],'Re-read source facts; matched start/end; Decimal arithmetic; cash-capex perimeter only')
# Negative-state counts and proper scores, pure Python sums.
w=openpyxl.load_workbook(io.BytesIO(file('Kraftmarkedet')),read_only=True,data_only=True);sheet=w['Strømpris'];sheet.reset_dimensions();rows=list(sheet.values)[2:]
for z in range(5):
 states=[float(x[z+1])<0 for x in rows];tr=states[:4344];test=states[4344:];q=sum(tr)/len(tr);probs=[]
 for prev in [False,True]:
  hits=[int(tr[i]) for i in range(1,len(tr)) if tr[i-1]==prev];probs.append(sum(hits)/len(hits))
 score=sum((probs[int(states[i-1])]-int(states[i]))**2 for i in range(4344,len(states)))/len(test);constant=sum((q-int(v))**2 for v in test)/len(test);run=0;lengths=[]
 for v in states:
  if v:run+=1
  elif run:lengths.append(run);run=0
 if run:lengths.append(run)
 a=R['financial']['zones']['NO'+str(z+1)];chk('NO'+str(z+1)+' events and score',sum(states)==a['negative_observations'] and len(lengths)==a['episodes'] and max(lengths)==a['max_run_observations'] and abs(score-a['brier_markov'])<1e-12 and abs(constant-a['brier_constant'])<1e-12,'Independent Boolean event runs and Python sums; no calendar authentication')
# Voting boundaries: exact decimal arithmetic catches floating threshold errors.
eq=csvrows(file('eq_'),'utf-16');total=sum(Dec(x['Market Value(NOK)']) for x in eq)
for x in R['governance']['sensitivity']:
 eligible=[v for v in eq if abs(Dec(v['Voting'].rstrip('%'))-Dec(v['Ownership'].rstrip('%')))>=Dec(str(x['threshold_pp']))];value=sum(Dec(v['Market Value(NOK)']) for v in eligible)
 chk('Voting threshold '+str(x['threshold_pp']),len(eligible)==x['rows'] and value==Dec(str(x['value_nok'])),'Exact source-decimal comparison, not floating subtraction')
chk('Voting share denominator',abs(float(Dec(str(R['governance']['sensitivity'][1]['value_nok']))/total*100)-R['governance']['material_market_value_pct'])<1e-10,'All exported listed equities, not total fund')
# AI cells: independently inspect specific source sheets for all Nordic paired years.
ai=openpyxl.load_workbook(io.BytesIO(file('isoc_eb_ai')),read_only=True,data_only=True);cells={}
for sh in list(ai)[1:]:
 sh.reset_dimensions();rr=list(sh.values);meta={row[0]:row[2] for row in rr[:10] if len(row)>2 and row[0]};indicator=str(meta.get('Information society indicator',''));size=meta.get('Size classes in number of persons employed')
 if not indicator.startswith("Enterprises' AI technologies were developed by own employees") or size not in ['From 10 to 49 persons employed','250 persons employed or more']:continue
 ti=next(i for i,row in enumerate(rr) if row and row[0]=='TIME');years={j:int(v) for j,v in enumerate(rr[ti]) if j and v}
 for row in rr[ti+2:]:
  if not row or row[0] not in ['Norway','Sweden','Denmark','Finland']:continue
  for j,year in years.items():
   try:val=Dec(str(row[j]))
   except:continue
   cells[(row[0],year,size)]=val
for row in R['business']['gaps']:
 if row['geo'] not in ['Norway','Sweden','Denmark','Finland']:continue
 small=cells[(row['geo'],row['year'],'From 10 to 49 persons employed')];large=cells[(row['geo'],row['year'],'250 persons employed or more')];chk('AI '+row['geo']+' '+str(row['year']),abs(float(large-small)-row['gap_pp'])<1e-10,'Independent direct source cells; no sampling standard errors supplied')
# Consolidated fiscal accounts, source values and contraction classification.
fiscal={x['type']:x for x in csvrows(file('10721'),'cp1252',True)};observations=[]
for row in R['public_finance']['history']:
 col='Revenue and expenditure '+str(row['year'])+' General government';a=Dec(fiscal['A Total revenue'][col]);e=Dec(fiscal['E Total expenditure (B+D)'][col]);net=Dec(fiscal['F Net lending/borrowing (A-E)'][col]);chk('Fiscal '+str(row['year']),a==Dec(str(row['revenue_nok_million'])) and e==Dec(str(row['expenditure_nok_million'])) and abs(a-e-net)<=1,'Consolidated source row; NOK million; one-unit rounding tolerance');observations.append((row['year'],a,e))
contractions=[b[0] for a,b in zip(observations,observations[1:]) if b[1]<a[1]];both=[b[0] for a,b in zip(observations,observations[1:]) if b[1]<a[1] and b[2]>a[2]];chk('Fiscal asymmetric years',contractions==R['public_finance']['revenue_contraction_years'] and len(both)==7,'Nominal comparisons only; not causal stimulus estimate')
# Reproduction equality: analysis output from archived originals versus published payload.
recalc=json.loads((P/'screening.json').read_text())['studies'];chk('Reproduction equality',recalc==R,'All six study payloads re-created from source archive')
report={'calculation_status':'PASS','independence':'Second code path by the same AI session. Source bytes re-read; csv/Decimal, direct cells and QR solver used. Not independent external human peer review. Source interpretation and study design remain shared.','checks':checks,'warnings':[{'status':'WARNING','scope':'Credit','text':'Candidate gain is unresolved; intervals cross zero. Latest-vintage, exploratory evaluation.'},{'status':'NOT VERIFIED','scope':'Financial','text':'Calendar/time-zone/DST mapping of indexed workbook. No calendar trading or operational claim is published.'},{'status':'WARNING','scope':'Accounting','text':'Cash capex is not total investment; latest fiscal year ends differ.'},{'status':'NOT VERIFIED','scope':'Governance','text':'Incorporation fields absent; legal-domicile claim excluded. Issuer-specific explanations require further documents.'},{'status':'NOT VERIFIED','scope':'Business','text':'Sampling standard errors and matched firm histories unavailable; no inferential confidence intervals or causal claims.'},{'status':'NOT VERIFIED','scope':'Public finance','text':'Structural non-oil and inflation-adjusted fiscal response not estimated. Sample ends in 2024.'}],'recent_work_scope':'12 November code/methodology and source-manifest orientation only. No claim of complete re-audit or real-time replication of that release.','runtime':{'python':sys.version,'platform':platform.platform()}}
(P/'calculation_audit.json').write_text(json.dumps(report,indent=2));print('PASS',len(checks),'independent-path calculation checks')
