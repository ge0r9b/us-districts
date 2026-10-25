# QA-094: a county's cities list shows the COUNTY's own result in the thumbnails (Harris County TX 52/46, not the cities' sum 56/42), same as its row in the state's counties list.
# QA-096: a city's precinct list > globe: the map thumbnails show the city's numbers (were empty).
# QA-095: a state's district list (state senate) shows the official state total in the thumbnails (FL FEC 6,110,125 / 4,683,038).
import asyncio,sys,json,re,os
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:600]),flush=True); (None if c else F.append(m))
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()===t)||[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / ')"
ROWV="t=>{const r=[...document.querySelectorAll('#listView .lvrow')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()===t}); if(!r) return null; const v={}; (window.CANDS?[]:[]); return [...r.querySelectorAll('.sg')].map(s=>(s.dataset.party||'')).join(' | ')}"
def pcts(t):
  d={}
  for nm,v in re.findall(r'(Harris|Trump)[^/%]*?(\d+(?:\.\d)?)%',t): d[nm]=float(v)
  return d
async def go(pg,q):
  await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#gq'))); await pg.wait_for_timeout(500); await pg.evaluate("()=>document.getElementById('gq').focus()")
  await pg.keyboard.type(q,delay=20); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['webkit','chromium'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for st,co,city in [x for x in [('Texas','Harris','Houston city'),('Florida','Miami-Dade','Miami city'),('Arizona','Maricopa','Phoenix city')] if not os.environ.get('ST') or x[0] in os.environ['ST']]:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
        await go(pg,st)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(4500)
        row=await pg.evaluate(ROWV,co)
        await pg.touchscreen.tap(*(await pg.evaluate(NMXY,co))); await pg.wait_for_timeout(5000)
        th=await pg.evaluate(TH); rp=pcts(row or ''); tp=pcts(th)
        ok=rp and tp and all(abs(rp[k]-tp.get(k,-99))<0.6 for k in rp)
        ck(bool(ok),f"{eng} {st} > {co}: QA-094 the cities list shows the county's own result ({th!r} vs its row {row!r})",[th,row])
        xy=await pg.evaluate(NMXY,city)
        if not xy: ck(False,f"{eng} {co}: {city} row found"); await c.close(); continue
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
        t1=await pg.evaluate(TH)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGlobe'))); await pg.wait_for_timeout(3000)
        t2=await pg.evaluate(TH)
        ck(len(pcts(t2))==2 and pcts(t2)==pcts(t1),f"{eng} {city} > globe: QA-096 the map shows the city's numbers ({t2!r} vs list {t1!r})",[t1,t2])
        ck(not er,f"{eng} {st}: no page errors",er); await c.close()
      if not os.environ.get('ST') or 'FLsen' in os.environ['ST']:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000); await go(pg,'Florida')
        await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
        await pg.evaluate("()=>document.querySelector('.lbtn[data-k=senate]').click()"); await pg.wait_for_timeout(4000)
        await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
        await pg.evaluate("m=>window.__setNum(m)",'num'); await pg.wait_for_timeout(2000)
        th=await pg.evaluate(TH)
        ck('6.11M' in th and '4.68M' in th,f"{eng} Florida state senate list: QA-095 the thumbnails show the official state total (6.11M / 4.68M): {th!r}",th)
        ck(not er,f"{eng} FL senate: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
