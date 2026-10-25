# Oct 25 1PM (1618): copy of h1200-cityN.py, saves all town rows; NJ/PA/NC/GA neighbour hunt + double-count check
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value||document.getElementById('gq').placeholder,list:document.body.classList.contains('listmode')})"
NM="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&(e.textContent.trim()===t||e.textContent.trim().startsWith(t+' ')));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for spec in sys.argv[3].split('#'):
      st,cn,tw,nb=spec.split('|'); nbs=[x for x in nb.split(';') if x]; R=out[st+'|'+tw]={}
      c,pg,log=await ctx(b,W,H,W<600,eng); tag=f"shotsb1621/b1621x-{eng[:2]}-{W}x{H}-cityN-{re.sub(r'[^A-Za-z0-9]','',tw)}"
      async def tapn(t):
        await pg.evaluate(NM,t); await pg.wait_for_timeout(400); xy=await pg.evaluate(NM,t)
        if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(6000)
        return xy
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      R['tapC']=await tapn(cn); crow=await pg.evaluate(ROWS)
      R['county']=[await pg.evaluate(HDR),await pg.evaluate(TH),len(crow),[r for r in crow if any(r.startswith(x) for x in [tw]+nbs)]]
      R['tapT']=await tapn(tw); rows=await pg.evaluate(ROWS)
      R['town']=[await pg.evaluate(HDR),await pg.evaluate(TH),len(rows),rows]
      R['suspect']=[r for r in rows if any(x.lower() in r.lower() for x in nbs)]
      await safeshot(pg,tag+'-list.png')
      await pg.evaluate("()=>window.__setNum&&window.__setNum('num')"); await pg.wait_for_timeout(1500)
      R['town_num']=[await pg.evaluate(TH),(await pg.evaluate(ROWS))[:4]]
      R['suspect_num']=[r for r in await pg.evaluate(ROWS) if any(x.lower() in r.lower() for x in nbs)]
      if R['suspect']:
        await safeshot(pg,tag+'-list-num.png')
        nm=R['suspect'][0].split(' | ')[0].strip(); R['tapS']=[nm,await tapn(nm)]
        R['afterS']=[await pg.evaluate(HDR),await pg.evaluate(TH),(await pg.evaluate(ROWS))[:3]]
        await safeshot(pg,tag+'-tapSuspect.png')
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(json.dumps({spec:R}),flush=True); await c.close()
    json.dump(out,open(f"b1621x-cityN-{eng}-{W}x{H}-{sys.argv[4]}.json",'w'),indent=1); await b.close()
asyncio.run(main())
