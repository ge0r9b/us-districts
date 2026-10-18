# b1574: quick re-check of QA-039/040 (2016 drill-in totals) at 1024x768 Chromium
import asyncio,json,re
from playwright.async_api import async_playwright
from common import *
FIND="""(pats)=>{const h=document.body.innerHTML;const o={};for(const p of pats){const re=new RegExp(p,'g');o[p]=[...new Set((h.match(re)||[]))].slice(0,6)}return o}"""
CAND="()=>[...document.querySelectorAll('[aria-label]')].filter(e=>e.offsetParent&&/Trump|Clinton/.test(e.getAttribute('aria-label'))).map(e=>[e.getAttribute('aria-label'),e.innerText.replace(/\\n/g,' '),e.title||''])"
async def tapname(pg,n):
  return await pg.evaluate("n=>{const r=[...document.querySelectorAll('#listView .lvrow.la .nmx')].find(x=>x.textContent.trim()===n);if(!r)return false;r.click();return true}",n)
async def main():
  o={}
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(7000)
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
    o['states']=await pg.evaluate(CAND)
    await tapname(pg,'PA'); await pg.wait_for_timeout(7000)
    o['PA_cands']=await pg.evaluate(CAND); o['PA_find']=await pg.evaluate(FIND,[r'2,9[27]\d,\d{3}',r'29[27]\d{4}'])
    o['PA_tot']=await pg.evaluate("()=>{try{return window.__stTot('Pennsylvania','2016')}catch(e){return String(e)}}")
    await pg.screenshot(path='../shots/b1574-ch-1024x768-y16-PA-counties.png')
    await tapname(pg,'Philadelphia'); await pg.wait_for_timeout(8000)
    o['PhCo_cands']=await pg.evaluate(CAND); o['PhCo_find']=await pg.evaluate(FIND,[r'58\d,\d{3}',r'10\d,\d{3}'])
    o['PhCo_rows']=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>r.innerText.replace(/\\n/g,' | '))")
    await pg.screenshot(path='../shots/b1574-ch-1024x768-y16-phila.png')
    await tapname(pg,'Philadelphia city'); await pg.wait_for_timeout(10000)
    o['Prec_cands']=await pg.evaluate(CAND); o['Prec_find']=await pg.evaluate(FIND,[r'58\d,\d{3}',r'10\d,\d{3}'])
    await pg.screenshot(path='../shots/b1574-ch-1024x768-y16-lvl4.png')
    o['E16_phila']=await pg.evaluate("()=>window.ELECTION2016&&window.ELECTION2016['Pennsylvania|Philadelphia County']")
    o['err']=log['pageerr']
    await c.close(); await b.close()
  print(json.dumps(o,indent=0)[:4000])
asyncio.run(main())
