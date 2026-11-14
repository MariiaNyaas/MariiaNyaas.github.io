"""Reproducible analysis for the 14 November 2026 release."""
from __future__ import annotations
import hashlib,json,math,pathlib,re,sys,warnings
import numpy as np
import openpyxl
import pandas as pd
warnings.filterwarnings("ignore", category=UserWarning)
S=pathlib.Path(sys.argv[1]); O=pathlib.Path(__file__).parent; CUTOFF="2026-11-14"
R={"status":"PUBLICATION CANDIDATE","cutoff":CUTOFF,"studies":{}}
rng=np.random.default_rng(20261114)

def scalar(x):
 if isinstance(x,dict): return {str(k):scalar(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)): return [scalar(v) for v in x]
 if isinstance(x,np.ndarray): return scalar(x.tolist())
 if isinstance(x,np.integer): return int(x)
 if isinstance(x,(float,np.floating)): return float(x) if np.isfinite(x) else None
 return x

def jsonstat_rows(path):
 d=json.loads(path.read_text()); ids,sizes=d["id"],d["size"]; cats=[]
 for key in ids:
  cat=d["dimension"][key]["category"]; order=cat.get("index")
  codes=[k for k,_ in sorted(order.items(),key=lambda kv:kv[1])] if isinstance(order,dict) else list(cat["label"])
  cats.append([(c,cat["label"].get(c,c)) for c in codes])
 values=d["value"]; out=[]
 for flat in range(int(np.prod(sizes))):
  rem=flat; coords=[0]*len(sizes)
  for j in range(len(sizes)-1,-1,-1): coords[j],rem=rem%sizes[j],rem//sizes[j]
  row={ids[j]:cats[j][coords[j]][0] for j in range(len(ids))}
  row.update({ids[j]+"_label":cats[j][coords[j]][1] for j in range(len(ids))})
  row["value"]=values[flat] if flat<len(values) else None; out.append(row)
 return out,d

def block_ci(values,block,draws=4000):
 a=np.asarray(values,float); means=[]
 for _ in range(draws):
  starts=rng.integers(0,len(a),size=math.ceil(len(a)/block)); ix=np.concatenate([(s+np.arange(block))%len(a) for s in starts])[:len(a)]
  means.append(a[ix].mean())
 return [float(x) for x in np.quantile(means,[.025,.975])]

# 1 Credit risk: rate transmission into reported repayment strain.
rates,_=jsonstat_rows(S/"ssb_10745_response.json"); strain,_=jsonstat_rows(S/"ssb_12128_response.json")
rate_df=pd.DataFrame(rates); rate_df=rate_df[(rate_df.Utlanstype=="04")&(rate_df.Sektor=="04b")].copy(); rate_df["year"]=rate_df.Tid.str[:4].astype(int); rate_df["value"]=pd.to_numeric(rate_df.value,errors="coerce")
annual_rate=rate_df.groupby("year",as_index=False).value.mean().rename(columns={"value":"mortgage_rate_pct"})
strain_df=pd.DataFrame(strain); strain_df["year"]=strain_df.Tid.astype(int); strain_df["value"]=pd.to_numeric(strain_df.value,errors="coerce")
mortgage=strain_df[strain_df.OkonomiskRomslig=="06"].copy(); wide=mortgage.pivot(index="year",columns="Inntekstgruppe",values="value")
aligned=annual_rate.set_index("year").join(wide).dropna(subset=["000"]).reset_index(); backtest=[]
for target_year in sorted(aligned.year):
 origin=target_year-1; train=aligned[aligned.year<=origin].dropna(subset=["000","mortgage_rate_pct"]); target=aligned[aligned.year==target_year]
 if len(train)<5 or target.empty: continue
 X=np.column_stack([np.ones(len(train)),train["000"],train.mortgage_rate_pct]); y=train["000"].shift(-1); valid=y.notna()
 if valid.sum()<4: continue
 beta=np.linalg.lstsq(X[valid],y[valid],rcond=None)[0]; row=train.iloc[-1]
 backtest.append({"year":int(target_year),"actual":float(target.iloc[0]["000"]),"model":float(np.array([1,row["000"],row.mortgage_rate_pct])@beta),"persistence":float(row["000"])})
credit_loss=np.array([abs(x["actual"]-x["persistence"])-abs(x["actual"]-x["model"]) for x in backtest])
credit_history=[{"year":int(r.year),"mortgage_rate_pct":r.mortgage_rate_pct,"all_pct":r.get("000"),"q1_pct":r.get("41"),"q2_pct":r.get("42"),"q3_pct":r.get("43"),"q4_pct":r.get("44")} for _,r in aligned.iterrows()]
latest_rate=rate_df.dropna(subset=["value"]).sort_values("Tid").iloc[-1]; latest_credit=aligned.sort_values("year").iloc[-1]
R["studies"]["credit"]={"title":"The Repayment-Strain Transmission Test","question":"Do mortgage rates add forward information about reported payment problems beyond persistence?","history":credit_history,"backtest":backtest,"model_mae":float(np.mean([abs(x["actual"]-x["model"]) for x in backtest])),"baseline_mae":float(np.mean([abs(x["actual"]-x["persistence"]) for x in backtest])),"mae_improvement_ci":block_ci(credit_loss,2),"latest_rate":{"month":latest_rate.Tid,"value":latest_rate.value},"latest_strain":{"year":int(latest_credit.year),"all":latest_credit["000"],"q1":latest_credit.get("41")},"limits":"Annual survey percentages are not arrears balances, PD or bank losses. Small latest-vintage sample; survey and rate revisions are not archived in real time. The regression is exploratory and its forecast origins are not independent."}

# 2 Financial: frozen long-only cross-zone power-price weights.
wb=openpyxl.load_workbook(S/"Kraftmarkedet_NO_2025.xlsx",read_only=True,data_only=True); sh=wb["Strømpris"]; sh.reset_dimensions(); raw=list(sh.values)
prices=np.array([[float(v) for v in row[1:6]] for row in raw[2:]],float)*10; zones=["NO1","NO2","NO3","NO4","NO5"]; split=len(prices)//2; train,test=prices[:split],prices[split:]
cov=np.cov(train,rowvar=False); inv=np.linalg.pinv(cov+.10*np.diag(np.diag(cov))); w=inv@np.ones(5); w=np.clip(w,0,None); w=w/w.sum(); equal=np.ones(5)/5
model_series,equal_series=test@w,test@equal; power_loss=(equal_series-equal_series.mean())**2-(model_series-model_series.mean())**2
blocks=[]
for i in range(0,len(prices),24):
 b=prices[i:i+24]
 if len(b): blocks.append({"block":i//24+1,**{z:float(b[:,j].mean()) for j,z in enumerate(zones)}})
ct=np.corrcoef(train,rowvar=False); ce=np.corrcoef(test,rowvar=False)
R["studies"]["financial"]={"title":"The Power-Diversification Stress Test","question":"Can frozen cross-zone weights reduce held-out Norwegian power-price volatility?","zones":zones,"blocks":blocks,"weights":{z:float(v) for z,v in zip(zones,w)},"train_observations":split,"test_observations":len(test),"test_vol_model":float(np.std(model_series,ddof=1)),"test_vol_equal":float(np.std(equal_series,ddof=1)),"test_vol_zones":{z:float(np.std(test[:,j],ddof=1)) for j,z in enumerate(zones)},"variance_improvement_ci":block_ci(power_loss,168),"mean_pair_correlation_train":float(ct[np.triu_indices(5,1)].mean()),"mean_pair_correlation_test":float(ce[np.triu_indices(5,1)].mean()),"zone_means":{z:float(prices[:,j].mean()) for j,z in enumerate(zones)},"limits":"The workbook has 8,760 indexed observations but clock time, time zone and DST alignment remain NOT VERIFIED. Price-index volatility is not investment return, dispatch profit or an executable hedge. Long-only weights use a stated ridge and were selected after inspecting this dataset."}

# 3 Accounting: capex-intensity persistence audit from annual SEC facts.
tags={"cfo":["NetCashProvidedByUsedInOperatingActivities"],"capex":["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsToAcquireProductiveAssets"]}; annual=[]
for p in sorted(S.glob("sec_companyfacts*.json")):
 d=json.loads(p.read_text()); facts=d["facts"].get("us-gaap",{}); periods={}
 for metric,choices in tags.items():
  cand=[]
  for priority,tag in enumerate(choices):
   for v in facts.get(tag,{}).get("units",{}).get("USD",[]):
    if v.get("form")!="10-K" or v.get("filed","9999")>CUTOFF or not v.get("start"): continue
    duration=(pd.Timestamp(v["end"])-pd.Timestamp(v["start"])).days
    if 330<=duration<=380 and v["end"]>="2015-01-01": cand.append((v["end"],v["filed"],v["accn"],-priority,tag,v))
  for end,filed,accn,_,tag,v in sorted(cand): periods.setdefault(end,{})[metric]={"value":v["val"],"tag":tag,"filed":filed,"accn":accn,"start":v["start"],"end":end}
 for end,m in sorted(periods.items()):
  if "cfo" in m and "capex" in m and m["cfo"]["value"]>0: annual.append({"company":d["entityName"],"cik":d["cik"],"end":end,"cfo_usd":m["cfo"]["value"],"capex_usd":m["capex"]["value"],"intensity_pct":100*m["capex"]["value"]/m["cfo"]["value"],"metrics":m})
account_bt=[]
for company in sorted({x["company"] for x in annual}):
 rows=sorted([x for x in annual if x["company"]==company],key=lambda x:x["end"])
 for i in range(max(4,len(rows)-3),len(rows)):
  tr=rows[:i]; account_bt.append({"company":company,"end":rows[i]["end"],"actual":rows[i]["intensity_pct"],"model":float(np.median([x["intensity_pct"] for x in tr[-3:]])),"last_value":tr[-1]["intensity_pct"]})
companies=sorted({x["company"] for x in account_bt}); cluster_means=[]
for _ in range(4000):
 vals=[]
 for c in rng.choice(companies,len(companies),replace=True): vals += [abs(x["actual"]-x["last_value"])-abs(x["actual"]-x["model"]) for x in account_bt if x["company"]==c]
 cluster_means.append(np.mean(vals))
R["studies"]["accounting"]={"title":"The Capital-Intensity Memory Test","question":"Is a three-year median more reliable than the last reported capex-intensity ratio?","annual":annual,"backtest":account_bt,"model_mae":float(np.mean([abs(x["actual"]-x["model"]) for x in account_bt])),"baseline_mae":float(np.mean([abs(x["actual"]-x["last_value"]) for x in account_bt])),"cluster_ci":[float(x) for x in np.quantile(cluster_means,[.025,.975])],"limits":"The ratio uses cash capex and CFO, not total economic investment. CFO includes working-capital effects; cash capex excludes some leases and noncash additions. Six issuers and issuer-cluster resampling cannot establish a universal forecasting law. Fiscal years differ."}

# 4 Governance: single-name dominance in country-industry stewardship cells.
hold=pd.read_csv(S/"eq_20260630.csv",encoding="utf-16",sep=";"); hold["market_value_nok"]=pd.to_numeric(hold["Market Value(NOK)"],errors="coerce"); hold=hold.dropna(subset=["market_value_nok","Country","Industry"])
cell_rows=[]
for (country,industry),g in hold.groupby(["Country","Industry"],dropna=False):
 total=g.market_value_nok.sum(); shares=g.market_value_nok/total; top=g.loc[g.market_value_nok.idxmax()]; hhi=float((shares**2).sum())
 cell_rows.append({"country":country,"industry":industry,"holdings":len(g),"cell_value_nok":float(total),"top_name":top["Name"],"top_share_pct":float(100*shares.max()),"hhi":hhi,"effective_names":float(1/hhi)})
cell_rows.sort(key=lambda x:x["cell_value_nok"],reverse=True); eligible=[x for x in cell_rows if x["holdings"]>=3]; total_value=float(hold.market_value_nok.sum()); sensitivity=[]
for threshold in [30,40,50,60,70]:
 chosen=[x for x in eligible if x["top_share_pct"]>=threshold]; sensitivity.append({"threshold_pct":threshold,"cells":len(chosen),"value_pct":100*sum(x["cell_value_nok"] for x in chosen)/total_value})
dominant=[x for x in eligible if x["top_share_pct"]>=50]
R["studies"]["governance"]={"title":"The Stewardship-Cell Dominance Map","question":"Where does one issuer dominate a country-industry stewardship cell?","rows":cell_rows,"holdings":len(hold),"cells":len(cell_rows),"eligible_cells":len(eligible),"dominant_cells":len(dominant),"dominant_value_pct":100*sum(x["cell_value_nok"] for x in dominant)/total_value,"sensitivity":sensitivity,"limits":"One 30 June 2026 listed-equity snapshot. A country-industry cell is an analytical grouping, not a legal or voting-control perimeter. Market value is not risk contribution. No return history means backtesting and causal claims are not applicable."}

# 5 Business economics: matched AI consideration versus current-use measures.
ai_wb=openpyxl.load_workbook(next(S.glob("isoc_eb_ai*.xlsx")),read_only=True,data_only=True); ai_obs=[]
for sheet in list(ai_wb)[1:]:
 sheet.reset_dimensions(); rows=list(sheet.values); idx=next((i for i,r in enumerate(rows) if r and r[0]=="TIME"),None)
 if idx is None: continue
 meta={r[0]:r[2] for r in rows[:idx] if len(r)>2 and r[0] and r[2] is not None}; indicator=str(meta.get("Information society indicator",""))
 kind="use" if indicator.startswith("Enterprises using at least one") else "considered" if indicator.startswith("Enterprises that ever considered") else None
 if not kind: continue
 times={i:int(v) for i,v in enumerate(rows[idx]) if i and v}
 for row in rows[idx+2:]:
  if not row or not isinstance(row[0],str): continue
  for i,year in times.items():
   try: value=float(row[i])
   except (TypeError,ValueError,IndexError): continue
   ai_obs.append({"geo":row[0],"year":year,"size":meta["Size classes in number of persons employed"],"kind":kind,"value":value,"flag":str(row[i+1] or "") if i+1<len(row) else ""})
ai=pd.DataFrame(ai_obs); paired=ai.pivot_table(index=["geo","year","size"],columns="kind",values="value",aggfunc="first").dropna().reset_index(); paired["difference_pp"]=paired.considered-paired.use; business_rows=paired.to_dict("records"); latest_business=[]
for (geo,size),g in paired.groupby(["geo","size"]):
 r=g.sort_values("year").iloc[-1]; latest_business.append({k:scalar(r[k]) for k in ["geo","year","size","use","considered","difference_pp"]})
R["studies"]["business"]={"title":"The AI Consideration–Deployment Gap","question":"How far apart are reported AI consideration and current use within the same geography and size class?","observations":ai_obs,"rows":business_rows,"latest":latest_business,"limits":"Separate survey indicators are compared within identical geography, year and size class. This is not a firm-level funnel: respondents and questionnaire routing may differ, and 'ever considered' is not assumed to contain every current user. Repeated cross-sections; no sampling errors or microdata were supplied, so inferential confidence intervals are NOT VERIFIED."}

# 6 Public finance: component-rule forecast versus persistence.
f=pd.read_csv(next(S.glob("10721*")),sep=";",skiprows=1,encoding="cp1252").set_index("type"); fiscal=[]
for c in f:
 m=re.fullmatch(r"Revenue and expenditure (\d{4}) General government",c)
 if m:
  a=float(f.loc["A Total revenue",c]); e=float(f.loc["E Total expenditure (B+D)",c]); net=float(f.loc["F Net lending/borrowing (A-E)",c]); fiscal.append({"year":int(m[1]),"revenue_nok_million":a,"expenditure_nok_million":e,"net_nok_million":net,"reconciliation_nok_million":a-e-net})
fiscal.sort(key=lambda x:x["year"]); fa=pd.DataFrame(fiscal); fa["rev_growth"]=fa.revenue_nok_million.pct_change(); fa["exp_growth"]=fa.expenditure_nok_million.pct_change(); fiscal_bt=[]
for i in range(6,len(fa)):
 tr=fa.iloc[:i]; rg=float(tr.rev_growth.dropna().tail(5).median()); eg=float(tr.exp_growth.dropna().tail(5).median()); prev=tr.iloc[-1]; pred=prev.revenue_nok_million*(1+rg)-prev.expenditure_nok_million*(1+eg)
 fiscal_bt.append({"year":int(fa.iloc[i].year),"actual":float(fa.iloc[i].net_nok_million),"component_model":float(pred),"persistence":float(prev.net_nok_million)})
fiscal_bt=fiscal_bt[-10:]; fiscal_loss=np.array([abs(x["actual"]-x["persistence"])-abs(x["actual"]-x["component_model"]) for x in fiscal_bt]); drev=np.diff(fa.revenue_nok_million); dexp=np.diff(fa.expenditure_nok_million); dnet=np.diff(fa.net_nok_million); variance=np.var(dnet,ddof=1)
R["studies"]["public_finance"]={"title":"The Fiscal-Balance Forecasting Trap","question":"Does a component-based rule beat simple persistence for next-year net lending?","history":fiscal,"backtest":fiscal_bt,"model_mae_nok_million":float(np.mean([abs(x["actual"]-x["component_model"]) for x in fiscal_bt])),"baseline_mae_nok_million":float(np.mean([abs(x["actual"]-x["persistence"]) for x in fiscal_bt])),"mae_improvement_ci_nok_million":block_ci(fiscal_loss,2),"change_variance_contribution":{"revenue":float(np.cov(drev,dnet,ddof=1)[0,1]/variance),"negative_expenditure":float(np.cov(-dexp,dnet,ddof=1)[0,1]/variance)},"limits":"Nominal consolidated general-government flows, 1995–2024. This is not the structural non-oil budget balance, fiscal-rule headroom or a sovereign-credit model. The component rule is exploratory and latest-vintage; petroleum prices, inflation and revisions are not modelled. Variance contributions are accounting covariance shares, not causal effects."}

manifest=[]
for p in sorted(S.iterdir()):
 if p.is_file(): manifest.append({"file":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"extracted":CUTOFF})
(O/"extraction_manifest.json").write_text(json.dumps(manifest,indent=2)); (O/"results.json").write_text(json.dumps(scalar(R),indent=2,allow_nan=False))
print(json.dumps({"credit":[R["studies"]["credit"]["model_mae"],R["studies"]["credit"]["baseline_mae"],len(backtest)],"financial":[R["studies"]["financial"]["test_vol_model"],R["studies"]["financial"]["test_vol_equal"]],"accounting":[R["studies"]["accounting"]["model_mae"],R["studies"]["accounting"]["baseline_mae"],len(account_bt)],"governance":[len(cell_rows),len(dominant),R["studies"]["governance"]["dominant_value_pct"]],"business":len(business_rows),"public_finance":[R["studies"]["public_finance"]["model_mae_nok_million"],R["studies"]["public_finance"]["baseline_mae_nok_million"]]},indent=2))
