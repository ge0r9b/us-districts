# QA-130: All States list (US House on or off) > #bGeo or bottom field 'Pittsburgh' + Enter > close the sheet: the list shows the city's precincts (not hidden or empty), title names the city. Chromium + WebKit 390.
import asyncio,sys,os,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
CASES=[("Pittsburgh","Pittsburgh city",300),("Boston","Boston city",100),("Columbus","Columbus city",100)]
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for house in [0,1]:
        for how in ['bgeo','gq']:
          for q,city,mn in CASES:
            c=await b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
            await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
            await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2500)
            if house:
              await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
              await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3000)
              await pg.evaluate("()=>{ if(!document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(800)
            if how=='bgeo':
              await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
              await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input'); i&&i.focus()}"); await pg.wait_for_timeout(400)
            else:
              await pg.evaluate("()=>{const g=document.getElementById('gq'); g.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); g.focus()}"); await pg.wait_for_timeout(700)
            await pg.keyboard.type(q,delay=20); await pg.wait_for_timeout(1800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(8000)
            if await pg.evaluate("()=>!document.getElementById('sheet').hidden"): await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(3000)
            r=await pg.evaluate("()=>{const lv=document.getElementById('listView'); return {vis:!!(lv&&!lv.hidden&&lv.getBoundingClientRect().height>100&&getComputedStyle(lv).display!=='none'), rows:[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).length, cr:document.getElementById('crumbs').innerText.replace(/\\n/g,' ')}}")
            t=f"{eng} house={house} {how} {q}"
            ck(r['vis'] and r['rows']>=mn,f"{t}: list shows its precincts ({r['rows']} rows)",r); ck(city in r['cr'],f"{t}: title names {city}",r); ck(not er,f"{t}: no page errors",er); await c.close()
      await b.close()
  print("FAILED:",F) if F else print("ALL OK"); sys.exit(1 if F else 0)
asyncio.run(main())
