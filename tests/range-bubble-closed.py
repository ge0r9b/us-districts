# QA-086: range chart (2020>2024) with the time row CLOSED (and open): a thumbnail tap shows the white #iconBub beside the photo
# (never the old dark #partyBub), not over any photo or the right-hand buttons. WebKit + Chromium touch 390/375/320 and WebKit 1024x768.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
async def center(pg,sel):
  return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
SEEN="""(ms)=>new Promise(res=>{const o={icon:null,party:false};const t0=performance.now();const f=()=>{const i=document.getElementById('iconBub'),p=document.getElementById('partyBub');if(p)o.party=true;if(i&&!o.icon){const r=i.getBoundingClientRect();o.icon=[r.left,r.top,r.right,r.bottom].map(Math.round);o.txt=i.textContent;}if(performance.now()-t0<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"""
async def main():
  async with async_playwright() as p:
    for eng,sizes in [('webkit',[(390,844),(375,667),(320,568),(1024,768)]),('chromium',[(390,844)])]:
      b=await getattr(p,eng).launch()
      for W,H in sizes:
        for closed in [True,False]:
          c=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=(eng=='webkit' or W<600)); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
          await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
          await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(900)
          await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
          if closed: await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(900)
          await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
          await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2500)
          th=await pg.evaluate("()=>[...document.querySelectorAll('#cands img.dmt, #cands .dmoc')].filter(e=>e.offsetWidth).map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)})")
          btn=await pg.evaluate("()=>[...document.querySelectorAll('.rbtn,#bTime,#bChart')].filter(e=>e.offsetWidth).map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)})")
          key=f"{eng} {W}x{H} row {'closed' if closed else 'open'}"
          ck(len(th)>=3,f"{key}: range chart thumbnails present ({len(th)})",th)
          for t in th[:4]:
            s=asyncio.ensure_future(pg.evaluate(SEEN,1200)); await pg.wait_for_timeout(30)
            await pg.touchscreen.tap((t[0]+t[2])/2,(t[1]+t[3])/2); o=await s
            ov=lambda a,b: min(a[2],b[2])-max(a[0],b[0])>1 and min(a[3],b[3])-max(a[1],b[1])>1
            ck(o['icon'] and not o['party'],f"{key}: tap photo at {t[:2]}: white bubble '{o.get('txt')}', no dark bubble",o)
            if o['icon']: ck(not any(ov(o['icon'],q) for q in th) and not any(ov(o['icon'],q) for q in btn),f"{key}: bubble covers no photo or button",[o['icon'],th,btn])
            await pg.wait_for_timeout(3300)
          ck(not er,f"{key}: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
