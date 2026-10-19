# QA-084: split bar (gbar) list rows draw at their final height on the first painted frame of every drill-in and Back
# (no 30 px -> 44 px growth). Pass 25: also a COLD first visit (fresh page per check: load > All States > Split bar > MA > Worcester). Per-frame sample of the first 3 rows' top/height for 1.2 s after each tap. WebKit touch 390/375/320.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
SIZES=[(390,844),(375,667),(320,568)] if len(sys.argv)<3 else [tuple(map(int,s.split('x'))) for s in sys.argv[2].split(',')]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400]),flush=True); (None if c else F.append(m))
FR="""(ms)=>new Promise(res=>{const o=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const rows=[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).slice(0,3).map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.top),Math.round(r.height)]});const v=JSON.stringify(rows);if(!o.length||o[o.length-1][1]!==v)o.push([Math.round(t),v]);if(t<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"""
async def center(pg,sel):
  return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in SIZES:
      c=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4000)
      await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
      await pg.touchscreen.tap(*(await center(pg,'#chartBox .copts button[data-ch=gbar]'))); await pg.wait_for_timeout(2500)
      async def nmxy(t):
        return await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'nearest'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",t)
      async def run(name,xyf):
        xy=await xyf()
        if not xy: ck(False,f"{W}: {name} target found"); return
        await pg.wait_for_timeout(300); samp=asyncio.ensure_future(pg.evaluate(FR,1200)); await pg.wait_for_timeout(30)
        await pg.touchscreen.tap(*xy); fr=await samp; await pg.wait_for_timeout(1500)
        st=[json.loads(v) for t,v in fr]; fin=st[-1]
        # after the first frame that shows the new list, every row must already have its final height
        hs=[r[1] for s in st for r in s if s and len(s)==len(fin)]
        bad=[ (t,v) for t,v in fr if json.loads(v) and json.loads(v)!=fin and any(r[1]!=f[1] for r,f in zip(json.loads(v),fin)) ]
        ck(fin and all(r[1]>=40 for r in fin),f"{W}: {name}: split rows end tall (>=40 px)",fin)
        ck(not bad[1:] if bad and bad[0][0]<=20 else not bad,f"{W}: {name}: no short-row frame before the final rows",fr[:8])
      back=lambda: center(pg,'#bBack')
      for rep in range(2):
        await run(f'drill MA #{rep}',lambda: nmxy('MA')); await run(f'drill Worcester #{rep}',lambda: nmxy('Worcester'))
        await run(f'Back 1 #{rep}',back); await run(f'Back 2 #{rep}',back)
      ck(not er,f"{W}: no page errors",er); await c.close()
      for cold in ['MA','Worcester']:
        c=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4000)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .copts button[data-ch=gbar]'))); await pg.wait_for_timeout(2500)
        if cold=='Worcester':
          xy=await nmxy('MA'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3000)
        await run(f'COLD first visit, drill {cold}',lambda: nmxy(cold))
        ck(not er,f"{W}: cold {cold}: no page errors",er); await c.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
