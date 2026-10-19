# QA-089 (ruling: the no-layout-jump rule applies): the list thumbnails (#laCands) never move when the back chevron appears or goes:
# All States > MA (chevron appears) > Back (chevron goes); also MA > Worcester > Back. WebKit 390x844 and Chromium 1024x768, DPR 2, touch.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500]),flush=True); (None if c else F.append(m))
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
TH="()=>[...document.querySelectorAll('#laCands .lact img, #laCands .lact .lacn')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top)]})"
BB="()=>{const e=document.getElementById('bBack');if(!e)return null;const r=e.getBoundingClientRect();return r.height&&getComputedStyle(e).display!=='none'?[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]:null}"
async def main():
  async with async_playwright() as p:
    for eng,W,H in [('webkit',390,844),('chromium',1024,768)]:
      b=await getattr(p,eng).launch(); c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(4000)
      t0=await pg.evaluate(TH)
      steps=[('All States > MA','tap','MA'),('MA > Worcester','tap','Worcester'),('Back to MA','back',None),('Back to All States','back',None)]
      for nm,kind,arg in steps:
        xy=await pg.evaluate(NMXY,arg) if kind=='tap' else await pg.evaluate(CEN,'#bBack')
        if not xy: ck(False,f'{eng} {W}: {nm}: target found',arg); continue
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3500)
        t=await pg.evaluate(TH); bb=await pg.evaluate(BB)
        ck(t and t0 and t[0]==t0[0],f'{eng} {W}: {nm}: thumbnails stay put {t0[:2]} -> {t[:2]}',[t0,t])
        if bb and t:
          ov=[x for x in t if x[0]<bb[2]-6 and x[0]+30>bb[0]+6 and x[1]<bb[3]-6 and x[1]+30>bb[1]+6]
          ck(not ov,f'{eng} {W}: {nm}: chevron {bb} clear of the thumbnails',[bb,t])
      ck(not er,f'{eng} {W}: no page errors',er); await c.close(); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
