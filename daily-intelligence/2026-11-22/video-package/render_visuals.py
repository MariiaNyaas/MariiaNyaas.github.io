import json, math
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'shared'/'results'
OUT=Path(__file__).resolve().parent/'visuals'
OUT.mkdir(exist_ok=True)
NAVY='#0E1929'; GOLD='#CEB382'; IVORY='#F4F1EB'; SILVER='#ACB8C6'; BLUE='#5EA7C8'; RED='#D56A6A'
plt.rcParams.update({'font.family':'DejaVu Sans','axes.facecolor':NAVY,'figure.facecolor':NAVY,'text.color':IVORY,'axes.labelcolor':SILVER,'xtick.color':SILVER,'ytick.color':SILVER,'axes.edgecolor':'#33465e'})

specs={
'01-credit-risk':('credit','CREDIT RISK INTELLIGENCE','Interest-Burden Threshold','SSB · 2006–2025','Interest burden ≥15%','Housing payment problems','year','interest_burden_15plus_pct','housing_payment_problem_pct','pp','model_mae','baseline_mae','Candidate MAE','Persistence MAE','Rate pressure','Household cash flow','Payment strain','Survey strain is not exposure-weighted PD.'),
'02-financial':('financial','FINANCIAL INTELLIGENCE','Policy-Rate Signal','Norges Bank · EUR/NOK','EUR/NOK','Policy rate','date','eurnok','policy_rate','','model_mae','baseline_mae','Signal MAPE','No-change MAPE','Rate differential','Risk premium','EUR/NOK return','Latest-vintage holdout is not a tradable strategy.'),
'03-accounting':('accounting','ACCOUNTING & AUDIT','Working-Capital Warning','SEC Company Facts','CFO margin','Working-capital absorption','end','cfo_margin_pct','wc_absorption_pct','%','model_mae','baseline_mae','Candidate MAE','Persistence MAE','Receivables + inventory','Cash conversion','Margin pressure','Selective issuer panel; accounting definitions differ.'),
'05-business':('business','BUSINESS & ECONOMIC','Digital-Readiness Conversion','Eurostat · 10 countries','Digital basic','Enterprise AI use 2025','country_code','digital_basic_2024_pct','ai_use_2025_pct','%','model_mae','baseline_mae','LOO model MAE','Country baseline MAE','Digital readiness','Organisational capability','AI adoption','Cross-section, not a temporal or causal backtest.'),
'06-public-finance':('public_finance','PUBLIC FINANCE','Sovereign Rate Pass-Through','SSB · Norges Bank','Interest income','Interest expense','year','interest_income_nok_million','interest_expense_nok_million','NOK mn','model_mae_nok_million','baseline_mae_nok_million','Candidate MAE','Persistence MAE','Asset repricing','Debt refinancing','Net interest','Consolidation can conceal municipal stress.'),
'07-art-capital':('art','ART & CAPITAL','Museum Subsidy Resilience','SSB museum statistics','Total visits','Subsidy share','year','total_visits','subsidy_share_pct','','model_mae_visits','baseline_mae_visits','Candidate MAE','Persistence MAE','Visitors + pricing','Fixed cultural costs','Funding gap','Museum scope and accounting can change across years.')}

def base(title,kicker,source):
    fig=plt.figure(figsize=(10.8,19.2),dpi=100)
    fig.text(.07,.95,kicker,fontsize=17,color=GOLD,weight='bold')
    fig.text(.07,.905,title,fontsize=31,color=IVORY,weight='bold')
    fig.text(.07,.875,source,fontsize=15,color=SILVER)
    return fig

def finish(fig,path,note):
    fig.text(.07,.055,note,fontsize=14,color=SILVER,wrap=True)
    fig.text(.07,.025,'FINANCIAL & RISK INTELLIGENCE · 22 NOVEMBER 2026',fontsize=11,color=GOLD)
    fig.savefig(path,facecolor=NAVY,bbox_inches=None)
    plt.close(fig)

def series_data(d,key):
    if key=='accounting':
        rows=d['annual']; rows=[r for r in rows if r.get('company')=='MICROSOFT CORP']
    else: rows=d['history']
    return rows

for slug,s in specs.items():
    key,kicker,title,source,l1,l2,xk,y1,y2,unit,mkey,bkey,mlab,blab,a,b,c,limit=s
    d=json.loads((DATA/f'{key}.json').read_text())
    rows=series_data(d,key)
    # Evidence panel
    fig=base(title,kicker,'OBSERVED EVIDENCE · '+source)
    ax=fig.add_axes([.09,.38,.82,.40])
    xs=[str(r.get(xk,''))[:10] for r in rows]; yy1=[r.get(y1) for r in rows]; yy2=[r.get(y2) for r in rows]
    valid=[i for i,v in enumerate(yy1) if v is not None]
    ax.plot(valid,[yy1[i] for i in valid],color=GOLD,lw=4,marker='o',ms=5,label=l1)
    ax2=ax.twinx(); valid2=[i for i,v in enumerate(yy2) if v is not None]
    ax2.plot(valid2,[yy2[i] for i in valid2],color=BLUE,lw=4,marker='o',ms=5,label=l2)
    ticks=list(range(0,len(xs),max(1,len(xs)//5)))
    ax.set_xticks(ticks,[xs[i] for i in ticks],rotation=25,ha='right',fontsize=11)
    ax.grid(alpha=.18); ax.spines[['top','right']].set_visible(False); ax2.spines['top'].set_visible(False)
    ax.legend(loc='upper left',frameon=False,labelcolor=IVORY); ax2.legend(loc='upper right',frameon=False,labelcolor=IVORY)
    fig.text(.09,.31,'Observed series',fontsize=18,color=GOLD,weight='bold')
    fig.text(.09,.25,'The chart preserves different units and uses a second axis when required.\nIt describes the sample; it does not establish causality.',fontsize=17,color=IVORY,linespacing=1.5)
    finish(fig,OUT/f'{slug}-evidence.png','Primary-source observations; periods and units shown in the published dashboard.')
    # Validation panel
    fig=base(title,kicker,'MODEL VALIDATION · FORWARD HOLDOUT')
    ax=fig.add_axes([.16,.42,.68,.34]); vals=[d[mkey],d[bkey]]
    ax.bar([0,1],vals,color=[RED,GOLD],width=.55)
    ax.set_xticks([0,1],[mlab,blab],fontsize=15); ax.grid(axis='y',alpha=.2)
    for i,v in enumerate(vals): ax.text(i,v*1.03,f'{v:,.3f}',ha='center',fontsize=22,color=IVORY,weight='bold')
    verdict='CANDIDATE BEATS BASELINE' if vals[0]<vals[1] else 'CANDIDATE DOES NOT BEAT BASELINE'
    fig.text(.09,.31,verdict,fontsize=21,color=GOLD if vals[0]<vals[1] else RED,weight='bold')
    fig.text(.09,.24,'A richer model earns credibility only by outperforming\na simple, pre-declared benchmark out of sample.',fontsize=18,color=IVORY,linespacing=1.5)
    finish(fig,OUT/f'{slug}-validation.png',limit)
    # Mechanism panel
    fig=base(title,kicker,'MECHANISM · DECISION PATH')
    ax=fig.add_axes([.06,.34,.88,.48]); ax.axis('off')
    for i,(txt,col) in enumerate([(a,GOLD),(b,BLUE),(c,RED)]):
        y=.74-i*.29
        box=FancyBboxPatch((.08,y),.84,.17,boxstyle='round,pad=.02,rounding_size=.025',fc='#14253a',ec=col,lw=3)
        ax.add_patch(box); ax.text(.5,y+.085,txt,ha='center',va='center',fontsize=24,color=IVORY,weight='bold')
        if i<2: ax.annotate('',xy=(.5,y-.09),xytext=(.5,y-.01),arrowprops=dict(arrowstyle='-|>',lw=3,color=SILVER))
    fig.text(.09,.25,'DECISION RULE',fontsize=17,color=GOLD,weight='bold')
    fig.text(.09,.19,'Use the signal as a governed prompt.\nDo not convert a plausible mechanism into a forecast claim.',fontsize=18,color=IVORY,linespacing=1.5)
    finish(fig,OUT/f'{slug}-mechanism.png',limit)
    # Branded research end card. This is navigation, not a subtitle track.
    fig=base(title,kicker,'FULL RESEARCH · DATA · INTERACTIVE PLAYGROUND')
    fig.text(.09,.64,'Read the complete evidence',fontsize=26,color=GOLD,weight='bold')
    fig.text(.09,.56,'Methodology, audit trail and scenario laboratory\nare available at the address in the description.',fontsize=21,color=IVORY,linespacing=1.6)
    fig.text(.09,.36,'mariianyaas.github.io',fontsize=27,color=BLUE,weight='bold')
    finish(fig,OUT/f'{slug}-outro.png','Scenarios are assumptions, not forecasts.')

# Governance: portfolio-specific evidence
g=json.loads((DATA/'governance-meta.json').read_text())
fig=base('Voice-to-Capital Mismatch','RISK & GOVERNANCE','NBIM holdings + voting records')
ax=fig.add_axes([.12,.38,.76,.40]); ss=g['sensitivity']; x=[r['threshold_pp'] for r in ss]; y=[r['value_share_pct'] for r in ss]
ax.plot(x,y,color=GOLD,lw=5,marker='o',ms=10); ax.set_xlabel('Absolute gap threshold · percentage points',fontsize=14); ax.set_ylabel('Matched portfolio value · %',fontsize=14); ax.grid(alpha=.2)
fig.text(.09,.29,f"{g['holdings']:,} matched holdings",fontsize=25,color=IVORY,weight='bold')
fig.text(.09,.24,f"Weighted absolute gap: {g['weighted_abs_gap_pp']:.3f} pp",fontsize=21,color=GOLD)
finish(fig,OUT/'04-governance-evidence.png','Observed reconciliation result; it does not infer voting intent.')
fig=base('Voice-to-Capital Mismatch','RISK & GOVERNANCE','DENOMINATOR SENSITIVITY')
ax=fig.add_axes([.13,.40,.74,.34]); ax.bar([str(r['threshold_pp']) for r in ss],[r['holdings'] for r in ss],color=BLUE)
ax.set_xlabel('Gap threshold · pp',fontsize=14); ax.set_ylabel('Holdings above threshold',fontsize=14); ax.grid(axis='y',alpha=.2)
fig.text(.09,.28,'410 holdings ≥ 0.10 pp',fontsize=26,color=GOLD,weight='bold')
fig.text(.09,.23,'12.89% of matched portfolio value',fontsize=20,color=IVORY)
finish(fig,OUT/'04-governance-validation.png','Threshold sensitivity is descriptive, not predictive validation.')
fig=base('Voice-to-Capital Mismatch','RISK & GOVERNANCE','MECHANISM · RECONCILIATION PATH')
ax=fig.add_axes([.06,.34,.88,.48]); ax.axis('off')
for i,(txt,col) in enumerate([('Capital owned',GOLD),('Votes eligible and cast',BLUE),('Unresolved influence gap',RED)]):
    y=.74-i*.29; box=FancyBboxPatch((.08,y),.84,.17,boxstyle='round,pad=.02,rounding_size=.025',fc='#14253a',ec=col,lw=3); ax.add_patch(box); ax.text(.5,y+.085,txt,ha='center',va='center',fontsize=24,color=IVORY,weight='bold')
    if i<2: ax.annotate('',xy=(.5,y-.09),xytext=(.5,y-.01),arrowprops=dict(arrowstyle='-|>',lw=3,color=SILVER))
fig.text(.09,.22,'Reconcile share class, record date, lending and market rules.',fontsize=18,color=IVORY,wrap=True)
finish(fig,OUT/'04-governance-mechanism.png','Automated matching is not an external human review.')
fig=base('Voice-to-Capital Mismatch','RISK & GOVERNANCE','FULL RESEARCH · DATA · INTERACTIVE PLAYGROUND')
fig.text(.09,.64,'Read the complete evidence',fontsize=26,color=GOLD,weight='bold')
fig.text(.09,.56,'Methodology, audit trail and scenario laboratory\nare available at the address in the description.',fontsize=21,color=IVORY,linespacing=1.6)
fig.text(.09,.36,'mariianyaas.github.io',fontsize=27,color=BLUE,weight='bold')
finish(fig,OUT/'04-governance-outro.png','Scenarios are assumptions, not forecasts.')
