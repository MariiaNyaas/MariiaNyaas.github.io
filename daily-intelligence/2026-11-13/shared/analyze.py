"""NEW research screening, not publication-ready. python analyze.py SOURCE_DIR.
All monetary amounts retain original nominal units. No synthetic observations.
"""
import pathlib,sys,json,hashlib,re,warnings
import pandas as pd,numpy as np,openpyxl
from scipy.stats import spearmanr
warnings.filterwarnings('ignore',category=UserWarning)
S=pathlib.Path(sys.argv[1]);O=pathlib.Path(__file__).parent
R={'status':'DRAFT — NOT PUBLICATION CLEARED','cutoff':'2026-11-13','studies':{}}
def scalar(x):
 if isinstance(x,dict):return {str(k):scalar(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [scalar(v) for v in x]
 if isinstance(x,np.ndarray):return scalar(x.tolist())
 if isinstance(x,np.integer):return int(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x
manifest=[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'received':'2026-11-13 or earlier; original extraction dates retained in file'} for p in sorted(S.iterdir()) if p.is_file()]
# 1 Bankruptcy acceleration: different target from yesterday's one-month level model.
b=pd.read_csv(next(S.glob('08551*')),sep=';',skiprows=1,encoding='cp1252');hist=[]
for c in b:
 m=re.fullmatch(r'Bankruptcies (\d{4})M(\d{2}) 03 Oslo - Oslove',c)
 if m:hist.append((f'{m[1]}-{m[2]}',float(b.iloc[0][c])))
hist.sort();y=np.array([v for _,v in hist]);roll=np.convolve(y,np.ones(12),'valid');change=roll[12:]/roll[:-12]-1
# Target: next three monthly bankruptcy counts. Frozen lag+seasonal candidate.
X=[];Y=[];ds=[]
for t in range(24,len(y)-2):
 X.append([1,y[t-1],y[t-12:t].mean(),y[t-3:t].sum(),np.sin(2*np.pi*t/12),np.cos(2*np.pi*t/12)])
 Y.append(y[t:t+3].sum());ds.append(hist[t][0])
X=np.array(X);Y=np.array(Y);pred=[];base=[];actual=[];dates=[]
for j in range(len(Y)-36,len(Y)):
 # At origin j, targets j-2 and j-1 are not fully observed: purge them.
 coef=np.linalg.lstsq(X[:j-2],Y[:j-2],rcond=None)[0];pred.append(max(0,float(X[j]@coef)));t=24+j;base.append(float(y[t-12:t-9].sum()));actual.append(Y[j]);dates.append(ds[j])
R['studies']['credit']={'question':'Can bankruptcy acceleration be forecast before the quarterly total is observed?','title':'The Bankruptcy Acceleration Test','history':[{'date':d,'count':v} for d,v in hist],'rolling12_latest':roll[-1],'rolling12_yoy_pct':change[-1]*100,'forecast_horizon':'3 months; 2 overlapping target rows purged','validation':'latest-vintage expanding origin; overlapping errors, not independent trials','backtest':[dict(date=d,actual=a,model=p,seasonal_naive=n) for d,a,p,n in zip(dates,actual,pred,base)],'model_mae':np.mean(abs(np.array(actual)-pred)),'baseline_mae':np.mean(abs(np.array(actual)-base)),'limits':'Counts are not PD; Oslo only; no firm or credit denominator. Candidate fitted after seeing dataset; exploratory, not preregistered.'}
# 2 Negative-price clustering: no storage dispatch or profitability inference.
w=openpyxl.load_workbook(S/'Kraftmarkedet_NO_2025.xlsx',read_only=True,data_only=True);sh=w['Strømpris'];sh.reset_dimensions();rows=list(sh.values);prices=np.array([[float(v) for v in row[1:6]] for row in rows[2:]])*10
zones={}
for z in range(5):
 p=prices[:,z];neg=p<0;runs=[];n=0
 for b0 in neg:
  if b0:n+=1
  elif n:runs.append(n);n=0
 if n:runs.append(n)
 train=neg[:4344];test=neg[4344:];q0=float(train.mean());trans=[float(train[1:][train[:-1]==state].mean()) if np.any(train[:-1]==state) else q0 for state in [False,True]]
 preds=np.array([trans[int(v)] for v in neg[4343:-1]]);qtest=test.astype(float)
 zones['NO'+str(z+1)]={'negative_observations':int(neg.sum()),'negative_share_pct':100*neg.mean(),'episodes':len(runs),'max_run_observations':max(runs,default=0),'mean_run':np.mean(runs) if runs else 0,'transition_train':trans,'brier_markov':np.mean((preds-qtest)**2),'brier_constant':np.mean((q0-qtest)**2),'history':[{'block':i,'mean':float(a.mean()),'negative':int((a<0).sum())} for i,a in enumerate(p.reshape(365,24))]}
R['studies']['financial']={'title':'When Negative Power Prices Persist','question':'Does a negative-price state contain out-of-sample information beyond its unconditional frequency?','zones':zones,'limits':'Indexed 8760 observations; calendar and DST not authenticated. State persistence is not an executable trading strategy. Terminal zero row retained. Brier scores, not investment returns.'}
# 3 Cash funding, independent annual tag selection and source records.
tags={'cfo':['NetCashProvidedByUsedInOperatingActivities'],'capex':['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'],'dividends':['PaymentsOfDividends','PaymentsOfDividendsCommonStock'],'buybacks':['PaymentsForRepurchaseOfCommonStock']}
annual=[]
for p in sorted(S.glob('sec_companyfacts*.json')):
 d=json.loads(p.read_text());facts=d['facts'].get('us-gaap',{});periods={}
 for metric,choices in tags.items():
  candidates=[]
  for priority,tag in enumerate(choices):
   for v in facts.get(tag,{}).get('units',{}).get('USD',[]):
    if v.get('form')!='10-K' or v.get('filed','9999')>'2026-11-13' or not v.get('start'):continue
    dur=(pd.Timestamp(v['end'])-pd.Timestamp(v['start'])).days
    if not 330<=dur<=380 or v['end']<'2015-01-01':continue
    candidates.append((v['end'],v['filed'],v['accn'],-priority,tag,v))
  for end,filed,accn,rank,tag,v in sorted(candidates):periods.setdefault(end,{})[metric]={'value':v['val'],'tag':tag,'filed':filed,'accn':accn,'start':v['start'],'end':end}
 for end,m in sorted(periods.items()):
  if 'cfo' in m and 'capex' in m:
   cfo=m['cfo']['value'];cap=m['capex']['value'];annual.append({'company':d['entityName'],'cik':d['cik'],'end':end,'cfo_usd':cfo,'capex_usd':cap,'cash_after_capex_usd':cfo-cap,'capex_cfo_pct':100*cap/cfo if cfo else None,'metrics':m})
latest=[max([r for r in annual if r['company']==c],key=lambda r:r['end']) for c in sorted({r['company'] for r in annual})]
R['studies']['accounting']={'title':'The Cash Funding Frontier','question':'How much operating cash remains after reported cash capital expenditure?','annual':annual,'latest':latest,'limits':'Cash capex excludes some leases/noncash additions; CFO includes working-capital swings. Fiscal years differ; do not sum latest rows into a calendar-year total. Not an AI-specific spending measure. Missing payout tags remain missing.'}
# 4 Voting rights versus economic ownership; no imputation of absent domicile.
d=pd.read_csv(S/'eq_20260630.csv',encoding='utf-16',sep=';');d['v']=pd.to_numeric(d['Market Value(NOK)'])
for col in ['Voting','Ownership']:d[col+'_pct']=pd.to_numeric(d[col].astype(str).str.replace('%','',regex=False),errors='coerce')
known=d['Voting_pct'].notna()&d['Ownership_pct'].notna();d['wedge_pp']=(d['Voting_pct']-d['Ownership_pct']).round(2);d['wedge_ratio']=d['Voting_pct']/d['Ownership_pct'].replace(0,np.nan)
material=known&(d.wedge_pp.abs()>=.1)
rows=d.loc[known,['Name','Country','Industry','v','Voting_pct','Ownership_pct','wedge_pp','wedge_ratio']].rename(columns={'v':'market_value_nok'}).to_dict('records')
R['studies']['governance']={'title':'Ownership Without Equal Voice','question':'Where do reported voting rights diverge from economic ownership, and what does that change in stewardship triage?','rows':rows,'known_rows':int(known.sum()),'total_rows':len(d),'material_rows':int(material.sum()),'material_market_value_pct':100*d.loc[material,'v'].sum()/d.v.sum(),'missing_incorporation_rows':int(d['Incorporation Country'].isna().sum()),'limits':'Snapshot 30 June 2026. Rounded percentages; 0.1 percentage-point threshold is a sensitivity assumption. Differences may reflect share classes or reporting structure; issuer verification needed before attributing governance causes. No causal return or control inference.'}
# 5 Within-country size gap, not adoption-productivity regression.
w=openpyxl.load_workbook(next(S.glob('isoc_eb_ai*')),read_only=True,data_only=True);ai=[];inventory=[]
for sh in list(w)[1:]:
 sh.reset_dimensions();rows=list(sh.values);idx=next((i for i,r in enumerate(rows) if r and r[0]=='TIME'),None)
 if idx is None:continue
 meta={r[0]:r[2] for r in rows[:idx] if len(r)>2 and r[0] and r[2] is not None};inventory.append({'sheet':sh.title,'metadata':meta})
 if not str(meta.get('Information society indicator','')).startswith("Enterprises' AI technologies were developed by own employees"):continue
 times={i:str(v) for i,v in enumerate(rows[idx]) if i and v}
 for row in rows[idx+2:]:
  if not row or not isinstance(row[0],str):continue
  for i,t in times.items():
   try:v=float(row[i])
   except (ValueError,TypeError,IndexError):continue
   ai.append({'geo':row[0],'year':int(t),'size':meta['Size classes in number of persons employed'],'value':v,'flag':str(row[i+1] or '') if i+1<len(row) else '', 'sheet':sh.title})
R['studies']['business']={'title':'The In-House AI Capability Gap','question':'How does reported own-employee AI development differ by enterprise size within Nordic economies?','observations':ai,'metadata':inventory,'limits':'Repeated survey cross-sections, not firm panel; no causal firm-size effect. Different denominators prohibit averaging size classes. AI definition changes and flags require review before interpreting trends.'}
# 6 revenue-expenditure response, not energy dividend incidence.
f=pd.read_csv(next(S.glob('10721*')),sep=';',skiprows=1,encoding='cp1252').set_index('type');fh=[]
for c in f:
 m=re.fullmatch(r'Revenue and expenditure (\d{4}) General government',c)
 if m:
  a=float(f.loc['A Total revenue',c]);e=float(f.loc['E Total expenditure (B+D)',c]);net=float(f.loc['F Net lending/borrowing (A-E)',c]);fh.append({'year':int(m[1]),'revenue_nok_million':a,'expenditure_nok_million':e,'net_lending_nok_million':net,'net_revenue_pct':100*net/a,'reconciliation_nok_million':a-e-net})
fh.sort(key=lambda r:r['year']);a=np.array([r['revenue_nok_million'] for r in fh]);e=np.array([r['expenditure_nok_million'] for r in fh]);gr=a[1:]/a[:-1]-1;ge=e[1:]/e[:-1]-1
rho,pv=spearmanr(gr,ge);R['studies']['public_finance']={'title':'The Revenue–Spending Asymmetry','question':'Does spending adjust when consolidated government revenue falls?','history':fh,'revenue_contraction_years':[fh[i+1]['year'] for i in range(len(gr)) if gr[i]<0],'revenue_expenditure_growth_spearman':rho,'spearman_p_exploratory':pv,'limits':'Nominal general-government flows through 2024; petroleum exposure, inflation and policy confound associations. Not the structural non-oil budget balance or fiscal-rule headroom; no sovereign PD inference.'}
# Dependence-aware, seeded uncertainty; exploratory specification checks.
rng=np.random.default_rng(20261113)
def block_ci(values,block=6):
 a=np.asarray(values,float);n=len(a);means=[]
 for _ in range(2000):
  starts=rng.integers(0,n,size=int(np.ceil(n/block)));ix=np.concatenate([(t+np.arange(block))%n for t in starts])[:n];means.append(a[ix].mean())
 return list(np.quantile(means,[.025,.975]))
c=R['studies']['credit'];bt=c['backtest'];loss=np.array([abs(x['actual']-x['seasonal_naive'])-abs(x['actual']-x['model']) for x in bt]);c['mae_improvement_ci_blocks']={str(k):block_ci(loss,k) for k in [3,6,12]};c['mean_mae_improvement']=float(loss.mean())
for zone in R['studies']['financial']['zones']:
 z=int(zone[-1])-1;neg=prices[:,z]<0;train=neg[:4344];test=neg[4344:];q=train.mean();tr=R['studies']['financial']['zones'][zone]['transition_train'];pr=np.array([tr[int(v)] for v in neg[4343:-1]]);loss=(q-test)**2-(pr-test)**2
 R['studies']['financial']['zones'][zone]['brier_improvement_ci_blocks']={str(k):block_ci(loss,k) for k in [24,168]}
# Ownership thresholds and independent rows cannot establish control or causal returns.
g=R['studies']['governance'];g['sensitivity']=[{'threshold_pp':t,'rows':sum(abs(x['wedge_pp'])>=t for x in g['rows']),'value_nok':sum(x['market_value_nok'] for x in g['rows'] if abs(x['wedge_pp'])>=t)} for t in [.05,.1,.25,.5,1]]
# Gap computed from same country/year and exact large/small survey categories.
a=pd.DataFrame(ai);wide=a.pivot(index=['geo','year'],columns='size',values='value');gap=[]
for (geo,year),row in wide.iterrows():
 small=row.get('From 10 to 49 persons employed',np.nan);large=row.get('250 persons employed or more',np.nan)
 if pd.notna(small) and pd.notna(large):gap.append({'geo':geo,'year':int(year),'small':float(small),'large':float(large),'gap_pp':float(large-small)})
R['studies']['business']['gaps']=gap
pf=R['studies']['public_finance'];pf['growth']=[{'year':fh[i+1]['year'],'revenue_growth_pct':100*gr[i],'expenditure_growth_pct':100*ge[i]} for i in range(len(gr))];pf['spending_up_in_revenue_down_years']=int(sum((gr<0)&(ge>0)))
(O/'extraction_manifest.json').write_text(json.dumps(manifest,indent=2));(O/'screening.json').write_text(json.dumps(scalar(R),indent=2,allow_nan=False))
print('SIX NEW QUESTIONS SCREENED; PUBLICATION GATE NOT PASSED')
print('Credit',R['studies']['credit']['model_mae'],R['studies']['credit']['baseline_mae'])
print('Cash funding',[(r['company'],r['end'],round(r['capex_cfo_pct'],2)) for r in latest])
print('Voting wedge',R['studies']['governance']['material_rows'],R['studies']['governance']['material_market_value_pct'])
print('AI observations',len(ai),'sizes',sorted({r['size'] for r in ai}))
print('Fiscal',len(fh),'years; contraction years',R['studies']['public_finance']['revenue_contraction_years'])
