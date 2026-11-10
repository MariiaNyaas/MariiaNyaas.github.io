#!/usr/bin/env python3
"""Daily source check for Nordic Systemic Risk Monitor. Standard library only.
No imputation. Source failure preserves last valid observations and reports stale status.
"""
import datetime,json,pathlib,urllib.request,urllib.error,time
HERE=pathlib.Path(__file__).resolve().parent
OUT=HERE/"data.json"
COUNTRIES=["NOR","SWE","DNK","FIN","ISL"]
INDICATORS={"unemployment":"SL.UEM.TOTL.ZS","inflation":"FP.CPI.TOTL.ZG","gdp":"NY.GDP.MKTP.KD.ZG","credit":"FS.AST.PRVT.GD.ZS","npl":"FB.AST.NPER.ZS","capital":"FB.BNK.CAPA.ZS"}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"NordicFinancialResilienceMonitor/1.0 (academic open-data monitoring)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.load(response)
def latest(country,indicator):
    url=f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=80"
    data=get(url)
    if not isinstance(data,list) or len(data)<2 or not isinstance(data[1],list):
        raise ValueError(f"Unexpected World Bank response for {country}/{indicator}: {str(data)[:120]}")
    for obs in data[1]:
        value=obs.get("value")
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            return {"value":round(float(value),6),"year":str(obs["date"]),"indicator":indicator,"source":"World Bank Indicators API"}
    return None
def main():
    now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    previous={}
    if OUT.exists():
        try:previous=json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError,OSError):pass
    records={}
    errors=[]
    fetched=0
    for country in COUNTRIES:
        records[country]={}
        for key,indicator in INDICATORS.items():
            try:
                result=latest(country,indicator)
                if result:records[country][key]=result;fetched+=1
            except Exception as exc:
                errors.append(f"{country}/{indicator}: {type(exc).__name__}: {str(exc)[:140]}")
                prior=previous.get("countries",{}).get(country,{}).get(key)
                if prior:records[country][key]=prior
            time.sleep(.12)
    if fetched==0:
        records=previous.get("countries",records)
    status="ok" if not errors else ("partial" if fetched else "stale_source_failure")
    payload={"checked_at":now,"last_success":now if fetched else previous.get("last_success"),"status":status,"countries":records,"source":"https://api.worldbank.org/v2/","indicators":INDICATORS,"successful_series":fetched,"failed_series":len(errors),"errors":errors[:30],"methodology":"Latest non-null observations per country and series. Annual vintages vary. No imputation, no predictive claims."}
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print(f"Status {status}; fetched {fetched}/30 series; errors {len(errors)}")
    if fetched==0:
        raise SystemExit("No new source observations; previous valid data preserved and status marked stale")
if __name__=="__main__":main()
