# QA-138: geo menu > All States > state > county town list, then tap the '16 tick for the first time: the list must repaint with 2016 numbers in < 3 s (was 60-260 s freeze on 1622). TX Harris, WA King, IL Cook, MA Worcester; Chromium 390x844 and WebKit 1024x768, touch.
import asyncio,sys,os,json,time
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; LIM=float(os.environ.get('LIM','3')); F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
TH="()=>[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ')).join(' / ')"
RW="()=>[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).slice(0,3).map(e=>e.innerText.replace(/\\n/g,' ')).join(' | ')"
EXP={'Harris':'54%','King':'72%','Cook':'74%','Worcester':'51%'}
async def cen(pg,s): return await pg.evaluate("s=>{const r=document.querySelector(s).getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",s)
async def main():
  async with async_playwright() as p:
    for eng,W,H in [x for x in [('chromium',390,844),('webkit',1024,768)] if not os.environ.get('ONLY') or x[0]==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for st,co in [('TX','Harris'),('WA','King'),('IL','Cook'),('MA','Worcester')]:
        c=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=W<600); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150])); t=f"{eng} {W}x{H} {st} {co}"
        await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4500)
        await pg.touchscreen.tap(*(await cen(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await cen(pg,'li.la-row'))); await pg.wait_for_timeout(4000)
        for l in [st,co]:
          await pg.evaluate(NMXY,l); await pg.wait_for_timeout(300); await pg.touchscreen.tap(*(await pg.evaluate(NMXY,l))); await pg.wait_for_timeout(4000)
        cr=await pg.evaluate("()=>document.getElementById('crumbs').innerText"); r0=await pg.evaluate(RW); th0=await pg.evaluate(TH)
        ck(co in cr and await pg.evaluate("()=>document.body.classList.contains('listmode')"),f"{t}: town list open",cr)
        await pg.touchscreen.tap(*(await cen(pg,'#bTime'))); await pg.wait_for_timeout(1500)
        xy=await pg.evaluate("()=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();return [r.left+52,r.top+r.height/2]}")
        t0=time.time(); await pg.touchscreen.tap(*xy); dt=None; th=rw=None
        while time.time()-t0<LIM+60:
          await asyncio.sleep(0.1)
          try: th,rw,y=await asyncio.wait_for(pg.evaluate("()=>[("+TH+")(),("+RW+")(),window.__ysl.get()]"),2)
          except Exception: continue
          if EXP[co] in th.split(' / ')[0] and rw!=r0 and 'no data' not in rw and '%' in rw and y==[0,0]: dt=round(time.time()-t0,2); break
        print(f"     {t}: {dt}s  {th0} -> {th}  rows: {str(rw)[:120]}",flush=True)
        ck(dt is not None and dt<LIM,f"{t}: list repaints with 2016 ({EXP[co]}) in < {LIM}s",dt)
        t1=time.time(); await pg.evaluate("1"); ck(time.time()-t1<1,f"{t}: page responsive after",time.time()-t1)
        ck(not er,f"{t}: no page errors",er); await c.close()
      await b.close()
  print("FAILED:",F) if F else print("ALL OK"); sys.exit(1 if F else 0)
asyncio.run(main())
