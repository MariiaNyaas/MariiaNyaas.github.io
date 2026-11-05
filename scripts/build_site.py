#!/usr/bin/env python3
"""Build a static GitHub Pages site and auto-catalogue independent research."""
import json, shutil, html, re, sys
from pathlib import Path
from urllib.parse import urlparse

BASE='https://mariianyaas.github.io'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_site'
DOMAINS={
 'Credit Risk Intelligence':'credit-risk',
 'Financial Intelligence':'financial',
 'Accounting & Audit Intelligence':'accounting',
 'Risk & Governance Intelligence':'governance',
 'Business & Economic Intelligence':'business',
 'Public Finance Intelligence':'public-finance',
}
PALETTE='''<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0E1929;color:#F4F1EB;font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#CEB382;text-decoration:none}a:hover{text-decoration:underline}header,main,footer{max-width:1100px;margin:auto;padding:28px 24px}header{display:flex;justify-content:space-between;align-items:center;gap:18px;border-bottom:1px solid #37475D}nav{display:flex;gap:18px;flex-wrap:wrap}h1{font:normal clamp(2rem,5vw,3.4rem)/1.18 Georgia,serif;margin:10px 0 18px}h2{font:normal 1.6rem Georgia,serif}p,.muted{color:#ACB8C6}.kicker{color:#CEB382;letter-spacing:.18em;text-transform:uppercase;font-size:.75rem}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:30px 0}input,select{background:#152439;border:1px solid #53627A;border-radius:8px;color:#F4F1EB;padding:11px 12px;font:inherit}input{min-width:220px;flex:2}select{flex:1}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,285px),1fr));gap:16px}.card{background:#152439;border:1px solid #36475D;border-radius:13px;padding:22px;display:flex;flex-direction:column;gap:10px}.card a{font-weight:650}.meta{font-size:.8rem;color:#CEB382}.foot{border-top:1px solid #37475D;margin-top:35px;color:#ACB8C6} .empty{padding:25px;border:1px dashed #53627A;border-radius:12px} @media(max-width:600px){header{display:block}nav{margin-top:12px}}
</style>'''
def esc(x):return html.escape(str(x),quote=True)
def standard(record):
  if not isinstance(record,dict):raise ValueError('Metadata must be JSON object')
  for k in ('title','domain','summary','published','url'):
    if not isinstance(record.get(k),str) or not record[k].strip():raise ValueError(f'Missing/invalid {k}: {record}')
  if record['domain'] not in DOMAINS:raise ValueError('Unknown domain: '+record['domain'])
  if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',record['published']):raise ValueError('Invalid published date')
  from datetime import date
  date.fromisoformat(record['published'])
  u=urlparse(record['url'])
  if u.scheme!='https' or u.netloc!='mariianyaas.github.io':raise ValueError('Unapproved URL: '+record['url'])
  return {k:record[k] for k in ('title','domain','summary','published','url')}|{'status':record.get('status','published')}

def main():
  if OUT.exists():shutil.rmtree(OUT)
  OUT.mkdir()
  # Copy existing site without modifying the repository. Do not expose private config/code.  
  allowed_folders={'credit-risk','financial','accounting','governance','business','public-finance','daily-intelligence','early-warning-signals-norway','household-debt-pressure-index','art-capital'}
  for p in ROOT.iterdir():
    if p.name.startswith('.') or p.name in {'scripts','_site','__pycache__'}:continue
    if p.is_file() and p.suffix.lower() in {'.html','.css','.js','.json','.xml','.txt','.png','.jpg','.jpeg','.webp','.svg','.ico','.pdf'}:
      shutil.copy2(p,OUT/p.name)
    elif p.is_dir() and (p.name in allowed_folders or p.name in {'assets','images'}):shutil.copytree(p,OUT/p.name)
  # Expand validated daily research bundles into the publication staging area.
  from ingest_bundles import ingest
  ingest(ROOT/'inbox', OUT)
  data=[]
  registry=ROOT/'research.json'
  if registry.exists():
    items=json.loads(registry.read_text(encoding='utf-8'))
    if not isinstance(items,list):raise ValueError('research.json must be an array')
    for item in items:
      if item.get('status','published')=='published':data.append(standard(item))
  for p in sorted((OUT/'daily-intelligence').rglob('project.json')) if (OUT/'daily-intelligence').exists() else []:
    if not (p.parent/'index.html').exists():
      print('SKIP unpublished project (no index.html):',p)
      continue
    record=standard(json.loads(p.read_text(encoding='utf-8')))
    if record['status']=='published':data.append(record)
  unique={}
  for r in data:unique[r['url'].rstrip('/')+'/']=r
  data=sorted(unique.values(),key=lambda r:(r['published'],r['title']),reverse=True)
  (OUT/'research.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  # Domain pages are generated at publish-time only; original GitHub files remain unchanged.
  for domain,slug in DOMAINS.items():
    entries=[r for r in data if r['domain']==domain]
    cards=''.join('<article class="card"><span class="meta">'+esc(r['published'])+'</span><a href="'+esc(r['url'])+'">'+esc(r['title'])+' ↗</a><p>'+esc(r['summary'])+'</p></article>' for r in entries)
    if not cards:cards='<div class="empty">Research in development. New studies will appear here once published.</div>'
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(domain)} | Mariia Nyaas</title><meta name="description" content="Independent research and interactive financial intelligence: {esc(domain)}."><link rel="canonical" href="{BASE}/{slug}/">{PALETTE}</head><body><header><a href="/">MARIIA NYAAS</a><nav><a href="/">← All Disciplines</a><a href="/#research">Latest Research</a><a href="/#connect">Connect</a></nav></header><main><div class="kicker">Research Library · {len(entries)} published</div><h1>{esc(domain)}</h1><p>Independent research, transparent methods and decision-oriented analytics.</p><div class="controls"><input id="q" aria-label="Search studies" placeholder="Search research…"><select id="sort" aria-label="Sort studies"><option value="new">Newest first</option><option value="old">Oldest first</option><option value="az">Title A–Z</option></select></div><section id="cards" class="cards">{cards}</section><p id="empty" hidden>No research matches your search.</p></main><footer class="foot">Mariia Nyaas · Evidence. Insight. Decision.</footer><script>const box=document.querySelector('#cards'),input=document.querySelector('#q'),sort=document.querySelector('#sort'),cards=[...box.children];function filter(){{let a=cards.filter(x=>x.textContent.toLowerCase().includes(input.value.toLowerCase()));a.sort((x,y)=>{{if(sort.value==='az')return x.querySelector('a').textContent.localeCompare(y.querySelector('a').textContent);let d=x.querySelector('.meta').textContent.localeCompare(y.querySelector('.meta').textContent);return sort.value==='old'?d:-d;}});box.replaceChildren(...a);document.querySelector('#empty').hidden=a.length>0}}input.addEventListener('input',filter);sort.addEventListener('change',filter)</script></body></html>'''
    folder=OUT/slug;folder.mkdir(exist_ok=True)
    (folder/'index.html').write_text(page,encoding='utf-8')
  urls=[BASE+'/']+[BASE+'/'+s+'/' for s in DOMAINS.values()]+[r['url'] for r in data]
  from xml.sax.saxutils import escape
  xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+escape(u)+'</loc></url>\n' for u in dict.fromkeys(urls))+'</urlset>\n'
  (OUT/'sitemap.xml').write_text(xml,encoding='utf-8')
  (OUT/'.nojekyll').touch()
  print('Built',len(data),'published entries and',len(DOMAINS),'domain pages.')
if __name__=='__main__':
  try:main()
  except Exception as exc:print('BUILD FAILED:',exc,file=sys.stderr);sys.exit(1)
