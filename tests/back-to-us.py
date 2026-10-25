# QA-131: 'Pittsburgh' (or ZIP 15213) + Enter, then 'United States' + Enter: US title, 50/48, state zoom, no precinct heat or popup, field 'United States'; reload stays on the US. WebKit + Chromium, 390x844, 375x667, 320x568.
import asyncio,sys,os,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
S="()=>({cr:document.getElementById('crumbs').innerText.replace(/\\n/g,' '),th:[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / '),z:map.getZoom(),ph:document.getElementById('gq').placeholder,v:document.getElementById('gq').value,heat:__heatCount(),pop:document.querySelectorAll('.leaflet-popup').length})"
async def typ(pg,q):
  await pg.evaluate("()=>{const g=document.getElementById('gq'); g.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); g.focus()}"); await pg.wait_for_timeout(700)
  await pg.keyboard.type(q,delay=20); await pg.wait_for_timeout(1800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000)
def good(r): return r['cr'].strip()=='United States' and '50%' in r['th'] and '48%' in r['th'] and 3<=r['z']<=5 and r['heat']==0 and r['pop']==0 and r['ph']=='United States' and not r['v']
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['webkit','chromium'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for W,H in [(390,844),(375,667),(320,568)]:
        for first in ['Pittsburgh','15213']:
          c=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
          await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
          await typ(pg,first); await typ(pg,'United States'); r=await pg.evaluate(S); t=f"{eng} {W}x{H} {first}"
          ck(good(r),f"{t} > United States: the US",r)
          await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000); r=await pg.evaluate(S); ck(good(r),f"{t}: reload stays on the US",r)
          ck(not er,f"{t}: no page errors",er); await c.close()
      await b.close()
  print("FAILED:",F) if F else print("ALL OK"); sys.exit(1 if F else 0)
asyncio.run(main())
