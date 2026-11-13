"""Separate screening checks; not full methodological or publication audit."""
import json,pathlib,sys,csv,io,hashlib
from decimal import Decimal
import openpyxl
S=pathlib.Path(sys.argv[1]);O=pathlib.Path(__file__).parent;r=json.loads((O/'screening.json').read_text());checks=[]
def check(name,ok,scope):checks.append({'check':name,'status':'PASS' if ok else 'FAIL','scope':scope})
m=json.loads((O/'extraction_manifest.json').read_text());check('Source checksums',all(hashlib.sha256((S/x['file']).read_bytes()).hexdigest()==x['sha256'] for x in m),'Byte integrity only; does not authenticate upstream source')
# Re-read SEC records with Decimal, not analysis selector.
for row in r['studies']['accounting']['latest']:
 d=json.loads((S/('sec_companyfacts_'+str(row['cik']).zfill(10)+'_2026-11-13.json')).read_text());vals={}
 for metric in ['cfo','capex']:
  sel=row['metrics'][metric];items=d['facts']['us-gaap'][sel['tag']]['units']['USD'];hits=[v for v in items if all(v.get(k)==sel[k] for k in ['start','end','filed','accn'])];check(row['company']+' '+metric+' source record',len(hits)>0 and all(v['val']==sel['value'] for v in hits),'Verifies selected record, not semantic capex completeness');vals[metric]=Decimal(str(sel['value']))
 check(row['company']+' cash arithmetic',Decimal(str(row['cash_after_capex_usd']))==vals['cfo']-vals['capex'],'Independent decimal subtraction')
# CSV reader independent of pandas: no central/local aggregation.
p=next(S.glob('10721*'));rows=list(csv.DictReader(io.StringIO(p.read_text(encoding='cp1252').split('\n',1)[1]),delimiter=';'));bytype={x['type']:x for x in rows}
check('Fiscal balance identities',all(abs(Decimal(bytype['A Total revenue'][f"Revenue and expenditure {x['year']} General government"])-Decimal(bytype['E Total expenditure (B+D)'][f"Revenue and expenditure {x['year']} General government"])-Decimal(bytype['F Net lending/borrowing (A-E)'][f"Revenue and expenditure {x['year']} General government"]))<=1 for x in r['studies']['public_finance']['history']),'30 years; one NOK million rounding tolerance')
# Re-read hourly source and count with pure Python.
w=openpyxl.load_workbook(S/'Kraftmarkedet_NO_2025.xlsx',read_only=True,data_only=True);sh=w['Strømpris'];sh.reset_dimensions();rows=list(sh.values)[2:]
for z in range(5):check('NO'+str(z+1)+' negative observations',sum(float(row[z+1])<0 for row in rows)==r['studies']['financial']['zones']['NO'+str(z+1)]['negative_observations'],'No timestamp or DST authentication')
a={'status':'SOURCE/ARITHMETIC CHECKS ONLY — SEE FULL AUDIT','checks':checks,'outside_this_script_scope':['Full economic interpretation and tag completeness','Robustness, dependence-adjusted uncertainty and sensitivity','Dashboard checks are outside this preliminary script','Desktop/mobile interactions and live deployment','Final editorial review is outside this preliminary script'],'independence':'Second code path by same AI session; not external human review. Some source selections shared.'};(O/'screening_audit.json').write_text(json.dumps(a,indent=2));print('Screening checks:',len(checks),'passed:',sum(x['status']=='PASS' for x in checks));print('Screening only; see audit.json for final publication assessment')
