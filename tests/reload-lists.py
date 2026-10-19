# Pass 33 note: a reload restores list views exactly: FL state house district list, FL counties > Miami-Dade cities list (snapshot, title, thumbnails, rows). Chromium + WebKit 390.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:700]),flush=True); (None if c else F.append(m))
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()===t)||[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
ST="()=>({list:document.body.classList.contains('listmode'),title:(document.getElementById('crumbs')||{}).innerText||'',n:document.querySelectorAll('#listView .lvrow.la').length,first:[...document.querySelectorAll('#listView .lvrow.la .nmx')].slice(0,3).map(e=>e.textContent),thumbs:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / ')})"
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for sc in ['flhouse','miami']:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#gq'))); await pg.wait_for_timeout(500); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type('Florida',delay=20); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200)
        if sc=='flhouse':
          await pg.evaluate("()=>document.querySelector('.lbtn[data-k=statehouse]').click()"); await pg.wait_for_timeout(4000)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(5000)
        if sc=='miami':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Miami-Dade'))); await pg.wait_for_timeout(5000)
        a=await pg.evaluate(ST)
        await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(400); s0=await pg.evaluate("()=>window.__stateSnapshot()")
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(13000)
        r=await pg.evaluate(ST); s1=await pg.evaluate("()=>window.__stateSnapshot()")
        s0.pop('ll',None); s1.pop('ll',None)
        ck(s0==s1,f"{eng} {sc}: reload restores the same saved state",[s0,s1])
        ck(a==r,f"{eng} {sc}: reload restores the same list (title, rows, thumbnails): {r['title']!r} {r['n']} {r['thumbs']!r}",[a,r])
        ck(not er,f"{eng} {sc}: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
