"""Reproduce from the 28 supplied source files; python analyze.py /path/to/sources.
Requires pandas, numpy, scipy, openpyxl. No network calls.
"""
import sys,json,re,hashlib,warnings
from pathlib import Path
import numpy as np,pandas as pd,openpyxl
from scipy import stats
# Explicit OLS implementation: HC3 and Bartlett Newey-West covariance.
class OLS:
 def __init__(self,y,X):
  self.names=list(X.columns) if isinstance(X,pd.DataFrame) else None
  self.y=np.asarray(y,dtype=float);self.X=np.asarray(X,dtype=float)
 def fit(self,cov_type=None,cov_kwds=None):
  X,y=self.X,self.y;n,k=X.shape;A=np.linalg.pinv(X.T@X);beta=np.linalg.lstsq(X,y,rcond=None)[0];u=y-X@beta
  if cov_type=='HC3':
   h=np.einsum('ij,jk,ik->i',X,A,X);U=X*(u/(1-h))[:,None];cov=A@(U.T@U)@A
  elif cov_type=='HAC':
   U=X*u[:,None];meat=U.T@U;L=cov_kwds['maxlags']
   for lag in range(1,L+1):
    cross=U[lag:].T@U[:-lag];meat+=(1-lag/(L+1))*(cross+cross.T)
   cov=A@meat@A
  else:cov=A*np.sum(u*u)/(n-k)
  self.params=pd.Series(beta,index=self.names) if self.names else beta
  se=np.sqrt(np.maximum(0,np.diag(cov)));crit=stats.norm.ppf(.975) if cov_type else stats.t.ppf(.975,n-k)
  self.ci=np.column_stack([beta-crit*se,beta+crit*se]);p=2*stats.norm.sf(abs(beta/np.maximum(se,1e-15)))
  self.pvalues=pd.Series(p,index=self.names) if self.names else p;self.rsquared=1-np.sum(u*u)/np.sum((y-y.mean())**2);return self
 def conf_int(self):return pd.DataFrame(self.ci,index=self.names) if self.names else self.ci
 def predict(self,X):return np.asarray(X)@np.asarray(self.params)
class SM:
 OLS=OLS
 @staticmethod
 def add_constant(x):
  if isinstance(x,pd.Series):return pd.DataFrame({'const':1.,x.name:x})
  return np.column_stack([np.ones(len(x)),x])
sm=SM()
warnings.filterwarnings('ignore',category=UserWarning)
S=Path(sys.argv[1]); O=Path(__file__).parent
R={}; manifest=[]
def clean(x):
 if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [clean(v) for v in x]
 if isinstance(x,np.ndarray):return clean(x.tolist())
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x
def dump(name,x): (O/name).write_text(json.dumps(clean(x),indent=2,ensure_ascii=False,allow_nan=False))
def num(v):
 try:return float(str(v).replace(',','.'))
 except:return np.nan
def ssb(prefix):return pd.read_csv(next(S.glob(prefix+'*')),sep=';',skiprows=1,encoding='cp1252')
def excel(prefix):
 w=openpyxl.load_workbook(next(S.glob(prefix+'*')),read_only=True,data_only=True);out=[]
 for sh in list(w)[1:]:
  sh.reset_dimensions();rows=list(sh.values);idx=next((i for i,r in enumerate(rows) if r and r[0]=='TIME'),None)
  if idx is None:continue
  meta={r[0]:r[2] for r in rows[:idx] if len(r)>2 and r[0] and r[2] is not None}
  times={i:str(v) for i,v in enumerate(rows[idx]) if i and v}
  for row in rows[idx+2:]:
   if not row or not isinstance(row[0],str):continue
   for c,t in times.items():
    v=num(row[c]) if c<len(row) else np.nan
    if np.isfinite(v):out.append(dict(meta,geo=row[0],time=t,value=v,flag=str(row[c+1] or '') if c+1<len(row) else '',sheet=sh.title))
 return pd.DataFrame(out)
for p in sorted(S.iterdir()):manifest.append({'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
dump('source_manifest.json',manifest)
# Credit: Oslo stable geography, all industries, bankruptcy counts; no rate denominator.
b=ssb('08551'); row=b.iloc[0];hist=[]
for c in b.columns:
 m=re.fullmatch(r'Bankruptcies (\d{4})M(\d{2}) 03 Oslo - Oslove',c)
 if m:hist.append({'date':f'{m[1]}-{m[2]}','count':num(row[c])})
bh=pd.DataFrame(hist).sort_values('date');y=bh['count'].values
# Expanding-origin log AR(1)+calendar seasonality; frozen specification; last 36 months.
dates=pd.to_datetime(bh.date); month=dates.dt.month.values
X=np.column_stack([np.ones(len(y)-1),np.log1p(y[:-1]),np.sin(2*np.pi*month[1:]/12),np.cos(2*np.pi*month[1:]/12)])
obs=np.log1p(y[1:]);pred=[]
for t in range(len(y)-36,len(y)):
 fit=sm.OLS(obs[:t-1],X[:t-1]).fit();pred.append(max(0,np.expm1(X[t-1]@fit.params)))
actual=y[-36:];naive=y[-48:-12];mae=float(np.mean(abs(actual-pred)));baseline=float(np.mean(abs(actual-naive)))
fit=sm.OLS(obs,X).fit(cov_type='HAC',cov_kwds={'maxlags':12})
R['credit']={'history':bh.to_dict('records'),'n':len(y),'backtest':[dict(date=d,actual=a,model=p,seasonal_naive=n) for d,a,p,n in zip(bh.date.iloc[-36:],actual,pred,naive)],'mae':mae,'naive_mae':baseline,'rmse':float(np.sqrt(np.mean((actual-pred)**2))),'hac_coefficients':fit.params,'hac_ci':fit.conf_int(),'r2':fit.rsquared,'nexus_status':'Not identified: only 10 half-year electricity-price observations, no firm-level matched defaults or exposure denominators.'}
# All Eurostat exports normalized with flags retained.
price=excel('nrg_pc_205'); ai=excel('isoc_eb_ai');prod=excel('nama_10_lp_ulc')
price.to_csv(O/'eurostat_prices_normalized.csv',index=False);ai.to_csv(O/'eurostat_ai_normalized.csv',index=False);prod.to_csv(O/'eurostat_productivity_normalized.csv',index=False)
pp=price[(price.Currency=='Euro')&(price.Taxes=='Excluding taxes and levies')&price['Energy consumption'].str.endswith('band IC')]
R['credit']['prices']=pp[['geo','time','value','flag']].to_dict('records')
# Storage: workbook hour index, not verified timestamps. 24-index blocks, 181 train /184 test.
w=openpyxl.load_workbook(S/'Kraftmarkedet_NO_2025.xlsx',read_only=True,data_only=True);sh=w['Strømpris'];sh.reset_dimensions();rows=list(sh.values);P=np.array([[num(v) for v in r[1:6]] for r in rows[2:]])*10
assert P.shape==(8760,5)
R['storage']={}; rng=np.random.default_rng(20261112)
for z in range(5):
 arr=P[:,z].reshape(365,24);train=arr[:181];test=arr[181:];pairs=[(a,b) for a in range(24) for b in range(a+1,24)]
 a,b=max(pairs,key=lambda ab:np.mean(.9*train[:,ab[1]]-train[:,ab[0]]));fixed=.9*test[:,b]-test[:,a]
 upper=np.maximum(0,np.max(np.array([.9*test[:,j]-test[:,i] for i,j in pairs]),axis=0))
 # No clipping fixed strategy: unconditional frozen dispatch cannot know future realised spread.
 samples=[]
 for _ in range(2000):
  starts=rng.integers(0,len(fixed),size=int(np.ceil(len(fixed)/7)));idx=np.concatenate([(i+np.arange(7))%len(fixed) for i in starts])[:len(fixed)];samples.append(fixed[idx].mean())
 sens=[{'efficiency':e,'mean_fixed':float(np.mean(e*test[:,b]-test[:,a]))} for e in [.8,.85,.9,.95]]
 R['storage']['NO'+str(z+1)]={'mean_price':float(P[:,z].mean()),'negative_hours':int((P[:,z]<0).sum()),'zero_hours':int((P[:,z]==0).sum()),'buy_index':a,'sell_index':b,'train_days':181,'test_days':184,'fixed_daily_mean':float(fixed.mean()),'upper_daily_mean':float(upper.mean()),'ci95_daily_mean':np.quantile(samples,[.025,.975]),'sensitivity':sens,'daily':[{'block':181+i,'fixed':f,'upper':u} for i,(f,u) in enumerate(zip(fixed,upper))],'monthly_mean':[float(a.mean()) for a in np.array_split(P[:,z],12)]}
R['storage_notes']=['Prices converted from øre/kWh to NOK/MWh by multiplying by 10.','Single 1 MWh charge per 24-index block, 1 MW input, 90% delivered energy; empty initial/final state. No overlapping reserve revenue.','Fixed hour pair trained on first 181 blocks and evaluated on last 184. No future-price clipping. Upper bound has perfect foresight and optional dispatch.','Workbook has hour index only and a final all-zone zero row; zeros retained as supplied, sensitivity excludes final block. Calendar/time-zone alignment is not authenticated.','Gross spread excludes fees, capex, grid charges, degradation and tax; not an investable return.']
R['storage']['NO1']['exclude_last_block_mean']=float(np.mean(np.array([d['fixed'] for d in R['storage']['NO1']['daily']])[:-1]))
# SEC annual flow selection with explicit tag and accession provenance.
tags={'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'],'cfo':['NetCashProvidedByUsedInOperatingActivities'],'capex':['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets'],'net_income':['NetIncomeLoss'],'da':['DepreciationDepletionAndAmortization','DepreciationDepletionAndAmortizationPropertyPlantAndEquipment','DepreciationAmortizationAndAccretionNet','Depreciation'],'assets':['Assets']}
sec=[]
for p in sorted(S.glob('Pasted*.txt')):
 j=json.loads(p.read_text());facts=j['facts'].get('us-gaap',{});records={}
 for metric,opts in tags.items():
  # Resolve each period separately across tag migrations. Prefer latest filing;
  # within the same filing use explicit priority. Do not add alternative tags.
  for rank,tag in reversed(list(enumerate(opts))):
   vals=[v for v in facts.get(tag,{}).get('units',{}).get('USD',[]) if v.get('filed','9999')<='2026-11-12' and v.get('form')=='10-K' and (metric=='assets' or (v.get('start') and 330<=(pd.Timestamp(v['end'])-pd.Timestamp(v['start'])).days<=380)) and v['end']>='2015-01-01']
   for v in vals:
    k=v['end'];old=records.setdefault(k,{}).get(metric)
    if old is None or (v['filed'],v['accn'])>=(old['filed'],old['accn']):records[k][metric]={'value':v['val'],'filed':v['filed'],'accn':v['accn'],'tag':tag,'start':v.get('start')}
 for end,metrics in records.items():
  if all(k in metrics for k in ['cfo','capex','net_income']):sec.append({'company':j['entityName'],'cik':j['cik'],'end':end,'metrics':metrics})
sec.sort(key=lambda x:(x['company'],x['end']));R['accounting']={'history':sec,'latest':[max([x for x in sec if x['company']==c],key=lambda x:x['end']) for c in sorted(set(x['company'] for x in sec))]}
# NBIM: listed values are issuer holdings. Real assets repeat country totals per property.
eq=pd.read_csv(S/'eq_20260630.csv',encoding='utf-16',sep=';');fi=pd.read_csv(S/'fi_20260630.csv',encoding='utf-16',sep=';')
eq['v']=pd.to_numeric(eq['Market Value(NOK)']);fi['v']=pd.to_numeric(fi['Market Value(NOK)']);issuer=eq.groupby('Name').v.sum().sort_values(ascending=False);total=issuer.sum();weights=issuer/total
R['governance']={'date':'2026-06-30','equity_total_nok':total,'bond_total_nok':fi.v.sum(),'issuers':len(issuer),'top10_pct':weights.head(10).sum()*100,'hhi':float((weights**2).sum()),'effective_n':float(1/(weights**2).sum()),'us_pct':float(eq.loc[eq.Country=='United States','v'].sum()/total*100),'top':[{'name':n,'nok':v,'weight_pct':v/total*100} for n,v in issuer.head(30).items()],'sectors':[{'name':n,'pct':v/total*100} for n,v in eq.groupby('Industry').v.sum().sort_values(ascending=False).items()],'cross_asset':[]}
for token in ['Microsoft','Alphabet','Amazon','Meta Platforms','NVIDIA','Oracle']:
 ev=eq.loc[eq.Name.str.contains(token,case=False,regex=False),'v'].sum();fv=fi.loc[fi.Name.str.contains(token,case=False,regex=False),'v'].sum();R['governance']['cross_asset'].append({'name':token,'equity_nok':ev,'bonds_nok':fv,'equity_pct':ev/total*100})
for kind in ['re','ri']:
 df=pd.read_csv(S/f'{kind}_20260630.csv',encoding='utf-16',sep=';');grp=df.groupby('Country')['Total country value'];assert grp.nunique().max()==1
 R['governance'][kind]={'rows':len(df),'country_total_nok':pd.to_numeric(grp.first()).sum(),'naive_row_sum_nok':pd.to_numeric(df['Total country value']).sum(),'country_values':grp.first().to_dict()}
# Adoption cross-section: EU27 members only; macro productivity not firm causal effect.
EU=['Belgium','Bulgaria','Czechia','Denmark','Germany','Estonia','Ireland','Greece','Spain','France','Croatia','Italy','Cyprus','Latvia','Lithuania','Luxembourg','Hungary','Malta','Netherlands','Austria','Poland','Portugal','Romania','Slovenia','Slovakia','Finland','Sweden']
a=ai[ai.sheet=='Sheet 9'].pivot(index='geo',columns='time',values='value');p=prod[prod.sheet=='Sheet 2'].pivot(index='geo',columns='time',values='value')
joined=pd.DataFrame({'ai2025':a['2025'],'ai2024':a['2024'],'ai2023':a['2023'],'productivity2025':p['2025'],'productivity2024':p['2024'],'productivity2023':p['2023']}).loc[EU].dropna();joined['growth2025']=(joined.productivity2025/joined.productivity2024-1)*100;joined['growth2024']=(joined.productivity2024/joined.productivity2023-1)*100;joined['ai_change']=joined.ai2025-joined.ai2023
f=sm.OLS(joined.growth2025,sm.add_constant(joined.ai2024)).fit(cov_type='HC3'); loo=[]
for c in joined.index:
 jn=joined.drop(c);loo.append(float(sm.OLS(jn.growth2025,sm.add_constant(jn.ai2024)).fit().params.iloc[1]))
base=joined.growth2024;forecast=f.predict(sm.add_constant(joined.ai2024))
# Genuine temporal holdout: train 2023 adoption ->2024 productivity, test 2024 adoption ->2025 growth.
f0=sm.OLS(joined.growth2024,sm.add_constant(joined.ai2023)).fit();oos=f0.predict(sm.add_constant(joined.ai2024));null=np.repeat(joined.growth2024.mean(),len(joined))
R['business']={'countries':joined.reset_index(names='geo').to_dict('records'),'n':len(joined),'beta_lagged_ai':f.params.iloc[1],'ci95':f.conf_int().iloc[1].tolist(),'p_hc3':f.pvalues.iloc[1],'r2':f.rsquared,'spearman':stats.spearmanr(joined.ai2024,joined.growth2025).statistic,'loo_beta_range':[min(loo),max(loo)],'oos_rmse':float(np.sqrt(np.mean((oos-joined.growth2025)**2))),'null_oos_rmse':float(np.sqrt(np.mean((null-joined.growth2025)**2))),'eu_ai':a.loc['European Union - 27 countries (from 2020)'].to_dict(),'eu_productivity':p.loc['European Union - 27 countries (from 2020)'].to_dict(),'size2025':{s:ai[(ai.sheet==s)&(ai.geo=='European Union - 27 countries (from 2020)')&(ai.time=='2025')].value.iloc[0] for s in ['Sheet 1','Sheet 13','Sheet 17']},'unweighted':True}
# Fiscal history: select consolidated general-government, not sum of subsectors.
fis=ssb('10721').set_index('type');energy=ssb('11561').set_index('energy balance item');fh=[];eh=[]
for year in range(1995,2025):
 c=f'Revenue and expenditure {year} General government';names=['A Total revenue','A1 Taxes on income, wealth etc','A2 Taxes on goods and services','A52 Dividends','A5512 Taxes on natural resources excluding extraction of petroleum','B7 Subsidies','E Total expenditure (B+D)','F Net lending/borrowing (A-E)','D1 Gross acquisitions of fixed assets and R&D'];fh.append(dict(year=year,**{n:num(fis.loc[n,c]) for n in names}))
for year in range(1990,2026):
 c=f'Energy balance (GWh) {year} Electricity';eh.append(dict(year=year,**{n:num(energy.loc[n,c]) for n in ['1 Primary energy production','2 Imports','3 Exports','12 Final energy consumption','9 Distribution losses']}))
R['public']={'fiscal':fh,'energy':eh,'quarterly_summary':'Excluded from fiscal modelling: supplied summary labelled NOK million, but 2026Q2 income 686 is inconsistent in scale with annual table. No silent conversion applied.'}
# ENTSO-E all supplied files inventoried and checked; aggregate load without extrapolating gaps.
ent={}
for file in sorted(S.glob('*.csv')):
 if file.name.startswith(('monthly_','physical_','inventory_','net_generation')):
  sep=',' if file.name.startswith('inventory_of_transmission') else '\t';d=pd.read_csv(file,sep=sep);entry={'rows':len(d),'columns':list(d.columns),'duplicate_rows':int(d.duplicated().sum())}
  if 'CountryCode' in d:
   d['t']=pd.to_datetime(d.DateUTC,dayfirst=True);entry['min']=str(d.t.min());entry['max']=str(d.t.max());entry['countries']=d.CountryCode.nunique();entry['duplicate_country_hour']=int(d.duplicated(['CountryCode','DateUTC']).sum());entry['load']=[{'country':c,'hours':len(g),'mean_mw':pd.to_numeric(g.Value_ScaleTo100).mean(),'peak_mw':pd.to_numeric(g.Value_ScaleTo100).max()} for c,g in d.groupby('CountryCode')]
  if 'ProvidedValue' in d:entry['missing_values']=int(pd.to_numeric(d.ProvidedValue,errors='coerce').isna().sum())
  if 'Month' in d:entry['months']=sorted(d.Month.unique().tolist())
  ent[file.name]=entry
R['entsoe']=ent
dump('results.json',R)
print(json.dumps(clean({'credit':{k:v for k,v in R['credit'].items() if k not in ['history','backtest','prices']},'storage':{k:{a:b for a,b in v.items() if a not in ['daily','monthly_mean']} for k,v in R['storage'].items()},'accounting_latest':R['accounting']['latest'],'governance':{k:v for k,v in R['governance'].items() if k not in ['top','sectors']},'business':{k:v for k,v in R['business'].items() if k not in ['countries','eu_productivity']},'public_latest':fh[-1],'energy_latest':eh[-1]}),indent=2))
