# QA-097: a city's map (county list > city > globe), with or without a chart picked, comes back as that city's map after a reload (not the county list). Chromium + WebKit 390.
import asyncio,sys,json,re,os
from playwright.async_api import async_playwright
URL="https://ge0r9b.github.io/us-districts/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:600]),flush=True); (None if c else F.append(m))
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()===t)||[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
ST="()=>({list:document.body.classList.contains('listmode'),title:(document.getElementById('crumbs')||{}).innerText||'',st:state.value,co:county.value,ch:window.chartMode||null,thumbs:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / ')})"
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for st,co,city,chart in [('Virginia','Fairfax','Vienna',None)]:
       try:
         c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
         await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
         await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#gq'))); await pg.wait_for_timeout(500); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type(st,delay=20); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
         await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200)
         await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(4500)
         print(eng,'build',await pg.evaluate('window.BUILD'),flush=True)
         print(await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow .nmx')].map(e=>e.textContent.trim()).filter(t=>/Fairfax|Vienna/.test(t))"),flush=True)
         await pg.touchscreen.tap(*(await pg.evaluate(NMXY,co))); await pg.wait_for_timeout(5000)
         print([e.textContent.trim() for e in []] or await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow .nmx')].filter(e=>e.offsetParent).map(e=>e.textContent.trim()).filter(t=>/Fairfax|Vienna/.test(t))"),flush=True)
         await pg.touchscreen.tap(*(await pg.evaluate(NMXY,city))); await pg.wait_for_timeout(5000)
         await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGlobe'))); await pg.wait_for_timeout(3000)
         if chart:
           await pg.evaluate("()=>{const b=document.querySelector('[aria-label=Chart]'); b&&b.click()}"); await pg.wait_for_timeout(600)
           await pg.evaluate("k=>{const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch===k); b&&b.click()}",chart); await pg.wait_for_timeout(2500)
         a=await pg.evaluate(ST); await pg.screenshot(path=f'shots37/b1616p37-{eng[:2]}-390x844-097-{city}-before.png')
         await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(400); sn=await pg.evaluate("()=>window.__stateSnapshot()")
         await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(12000)
         r=await pg.evaluate(ST); await pg.screenshot(path=f'shots37/b1616p37-{eng[:2]}-390x844-097-{city}-reload.png')
         ck(r['list']==a['list'],f"{eng} {city} (chart {a['ch']}): reload keeps the {'list' if a['list'] else 'map'} view",[a,r,sn])
         ck(r['title']==a['title'] and r['co']==a['co'],f"{eng} {city}: reload restores the city ({r['title']!r} vs {a['title']!r})",[a,r,sn])
         ck(r['thumbs']==a['thumbs'],f"{eng} {city}: reload restores the numbers ({r['thumbs']!r} vs {a['thumbs']!r})",[a,r])
         ck(not er,f"{eng} {city}: no page errors",er); await c.close()
       except Exception as ex: ck(False,f'{eng} {city}: flow error',str(ex)[:200]); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
