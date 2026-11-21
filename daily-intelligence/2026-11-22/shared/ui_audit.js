const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const base = process.argv[2] || 'http://127.0.0.1:8765/daily-intelligence/2026-11-22';
const out = process.argv[3] || path.join(__dirname, 'ui_audit.json');
const slugs = ['01-credit-risk','02-financial','03-accounting','04-governance','05-business','06-public-finance','07-art-capital'];
const checks=[];
const add=(name,ok,detail='')=>checks.push({name,status:ok?'PASS':'FAIL',detail:String(detail)});

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 for(const slug of slugs){
  const page=await browser.newPage({viewport:{width:1365,height:768}});const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  const response=await page.goto(`${base}/${slug}/`,{waitUntil:'networkidle'});
  add(`${slug} HTTP`,response&&response.ok(),response&&response.status());
  await page.waitForFunction(()=>document.documentElement.dataset.ready==='true',{timeout:15000}).catch(()=>{});
  add(`${slug} ready`,await page.evaluate(()=>document.documentElement.dataset.ready==='true'));
  add(`${slug} no runtime errors`,errors.length===0,errors.join(' | '));
  add(`${slug} three rendered charts`,await page.locator('.chart svg').count()===3,await page.locator('.chart svg').count());
  const disabled=await page.locator('button:disabled,input:disabled,select:disabled').count();add(`${slug} controls enabled`,disabled===0,disabled);
  const baseline=await page.locator('#result').innerText();const input=page.locator('#playground input').first();const old=await input.inputValue();const min=Number(await input.getAttribute('min'));const step=Number(await input.getAttribute('step'));let next=Number(old)+step;if(next>Number(await input.getAttribute('max')))next=min;
  await input.fill(String(next));await page.waitForTimeout(50);const changed=await page.locator('#result').innerText();add(`${slug} scenario input changes result`,changed!==baseline,`${baseline} -> ${changed}`);
  await page.locator('#reset').click();await page.waitForTimeout(50);add(`${slug} reset roundtrip`,(await page.locator('#result').innerText())===baseline);
  const select=page.locator('#choice');const options=await select.locator('option').count();add(`${slug} selector populated`,options>0,options);
  if(options>1){const chartBefore=await page.locator('#chart').innerHTML();await select.selectOption({index:1});await page.waitForTimeout(50);const chartAfter=await page.locator('#chart').innerHTML();add(`${slug} selector changes evidence`,chartAfter!==chartBefore);}else add(`${slug} selector changes evidence`,true,'single valid option');
  const dl1=page.waitForEvent('download');await page.locator('#export').click();const scenario=await dl1;add(`${slug} scenario export`,!!scenario.suggestedFilename(),scenario.suggestedFilename());
  const dl2=page.waitForEvent('download');await page.locator('#csv').click();const csv=await dl2;add(`${slug} CSV export`,csv.suggestedFilename().endsWith('.csv'),csv.suggestedFilename());
  await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'networkidle'});await page.waitForFunction(()=>document.documentElement.dataset.ready==='true',{timeout:15000}).catch(()=>{});const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1);add(`${slug} mobile no horizontal overflow`,!overflow,await page.evaluate(()=>`${document.documentElement.scrollWidth}/${document.documentElement.clientWidth}`));
  const columns=await page.locator('.controls').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length);add(`${slug} mobile controls stack`,columns===1,columns);
  await page.close();
 }
 await browser.close();
 const fail=checks.filter(x=>x.status==='FAIL').length;fs.writeFileSync(out,JSON.stringify({status:fail?'FAIL':'PASS',pass:checks.length-fail,fail,checks},null,2));console.log(JSON.stringify({status:fail?'FAIL':'PASS',pass:checks.length-fail,fail},null,2));process.exit(fail?1:0);
})().catch(error=>{console.error(error);process.exit(2)});
