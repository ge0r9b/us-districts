# QA-129: list view with a district type on; a city entered (bottom field Enter, #bGeo Enter, or a tapped suggestion row) clears the type and shows the CITY's numbers, not its county's. Chromium + WebKit 390.
import asyncio,sys,os,json,re
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
CASES=[("Pittsburgh","Pittsburgh city",70),("Boston","Boston city",70),("Columbus","Columbus city",66)]
S="()=>({cr:document.getElementById('crumbs').innerText.replace(/\\n/g,' '),th:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ')).slice(0,2),lt:__stateSnapshot().lt})"
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for how in ['enter','bgeo','row']:
        for q,city,minD in (CASES if how!='row' else CASES[:1]):
          c=await b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
          await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
          await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2500)
          await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
          await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3000)
          await pg.evaluate("()=>{ if(!document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(800)
          if how=='bgeo':
            await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
            await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input'); i&&i.focus()}"); await pg.wait_for_timeout(400)
          else:
            await pg.evaluate("()=>{const g=document.getElementById('gq'); g.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); g.focus()}"); await pg.wait_for_timeout(700)
          await pg.keyboard.type(q,delay=20); await pg.wait_for_timeout(1800)
          if how=='row': await pg.evaluate("c=>{const l=[...document.querySelectorAll('#gfs li, .geofs li')].filter(l=>l.offsetParent&&l.innerText.indexOf(c)>=0)[0]; l&&l.click()}",city)
          else: await pg.keyboard.press('Enter')
          await pg.wait_for_timeout(8000); r=await pg.evaluate(S)
          d=max([float(m) for t in r['th'] for m in re.findall(r'([\d.]+)%',t)[:1]]+[0])
          ck(city in r['cr'],f"{eng} {how} {q}: title names {city}",r); ck(r['lt']=='none',f"{eng} {how} {q}: district type cleared",r)
          ck(d>=minD,f"{eng} {how} {q}: city numbers (Harris {d}% >= {minD})",r); ck(not er,f"{eng} {how} {q}: no page errors",er); await c.close()
      await b.close()
  print("FAILED:",F) if F else print("ALL OK"); sys.exit(1 if F else 0)
asyncio.run(main())
