# QA-087: a DC address typed in the bottom field from a list view (All States list, PA > Philadelphia townships list) shows DC's own
# result (Harris ~90 / Trump ~6), as from the map, never the national list / US totals under a "District of Columbia" title. WebKit + Chromium 390.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500]),flush=True); (None if c else F.append(m))
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
ST="""()=>({crumbs:(document.getElementById('crumbs')||{}).innerText||'',ph:document.getElementById('gq').placeholder,
 thumbs:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,4).join(' / '),
 rows:[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).length,
 dcvis:(()=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()==='DC'); if(!e) return null; const r=e.getBoundingClientRect(); const bb=document.getElementById('barBottom'); const lim=bb?bb.getBoundingClientRect().top:innerHeight; return r.top>=0&&r.bottom<=lim;})(),
 states:[...document.querySelectorAll('#listView .lvrow .nmx')].filter(r=>r.offsetParent).map(e=>e.textContent.trim()).filter(t=>/^(CA|TX|FL|NY|PA)$/.test(t)).length})"""
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
async def main():
  async with async_playwright() as p:
    import os
    for eng in [e for e in ['webkit','chromium'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for sc in ['map','allstates','phila']:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
        if sc!='map':
          await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(4500)
        if sc=='phila':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3500)
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Philadelphia'))); await pg.wait_for_timeout(3500)
        await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
        await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
        a=await pg.evaluate(ST)
        pc=[int(x) for x in re.findall(r'(\d+)(?:\.\d)?\s*%',a['thumbs'])]
        ok=any(x>=85 for x in pc) and not any(45<=x<=55 for x in pc) 
        ck(ok,f"{eng} 390 from {sc}: DC's own result (Harris ~90 / Trump ~6) (same as tapping DC in the All States list)",a)
        if sc!='map': ck(a['dcvis'] is True,f"{eng} 390 from {sc}: the selected DC row is on screen (pass 28)",a)
        if sc!='map': await pg.screenshot(path=f"/tmp/addr-{eng[:2]}-{sc}.png")
        ck(not er,f"{eng} {sc}: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
