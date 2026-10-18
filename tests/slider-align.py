# build 1580: time slider endpoints from live rects + clock button fixed while the row opens/closes (QA-053)
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
VPS=[(390,844),(375,667),(320,568),(820,1180)]
REC="""()=>{ window.__fr=[]; const b=document.getElementById('bTime'); const f=()=>{ const r=b.getBoundingClientRect(); window.__fr.push([r.left,r.top,r.width,r.height]); if(window.__fr.length<400) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""
GEO="""()=>{ const c=x=>{const r=x.getBoundingClientRect(); return r.left+r.width/2;}; const ic=document.querySelector('#crumbs .cic'); const dots=[...document.querySelectorAll('#ysl .tk i')].map(c); const sp=[...document.querySelectorAll('#ysl .tk span')]; const bt=document.getElementById('bTime').getBoundingClientRect();
 return {d: ic&&ic.getBoundingClientRect().width>0?c(ic):null, dots, labs:sp.map(c), txt:sp.map(s=>s.textContent), fw:sp.map(s=>getComputedStyle(s).fontWeight), vis:sp.map(s=>getComputedStyle(s).display!=='none'&&s.getBoundingClientRect().width>0), ylb:[...document.querySelectorAll('#ysl .ylb')].map(e=>getComputedStyle(e).visibility), bl:bt.left}; }"""
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in VPS:
      for mode in ["map","list"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},is_mobile=W<800,has_touch=True); pg=await ctx.new_page()
        errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(2500)
        await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(3000)
        if mode=="list": await pg.evaluate("()=>{ if(!document.body.classList.contains('listmode')) document.getElementById('bGlobe').click() }"); await pg.wait_for_timeout(1500)
        if not await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(800)
        tag=f"{W}x{H} {mode}"
        await pg.evaluate(REC); await pg.wait_for_timeout(150)
        await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1200)
        g=await pg.evaluate(GEO)
        if W==390 and mode=="list": await pg.screenshot(path="/workspace/slider-390.png",timeout=120000)
        if W==390 and mode=="map": await pg.screenshot(path="/workspace/slider-390-map.png",timeout=120000)
        await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(900)
        fr=await pg.evaluate("()=>window.__fr")
        r0=fr[0]; dev=max(max(abs(a-b) for a,b in zip(r,r0)) for r in fr)
        ck(dev<=0.5,f"{tag}: clock rect fixed over {len(fr)} frames open+close (max dev {dev:.1f}px, {r0})")
        if g['d'] is not None:
          d=g['d']; D=g['dots']
          ck(abs(D[0]-d)<=1,f"{tag}: '16 dot {D[0]:.1f} on icon-column centre {d:.1f}")
          ck(abs((g['bl']-D[2])-d)<=1,f"{tag}: '24 dot {D[2]:.1f} is d={d:.1f} left of clock {g['bl']:.1f} (got {g['bl']-D[2]:.1f})")
          ck(abs(D[1]-(D[0]+D[2])/2)<=1,f"{tag}: '20 dot centred")
        else: ck(False,f"{tag}: no icon column")
        ck(g['txt']==["'16","'20","'24"] and all(g['vis']),f"{tag}: labels {g['txt']} visible")
        ck(all(abs(a-b)<=1 for a,b in zip(g['labs'],g['dots'])),f"{tag}: labels centred on dots")
        ck(all(int(x)<=500 for x in g['fw']),f"{tag}: labels regular weight {g['fw']}")
        ck(all(v=='hidden' for v in g['ylb']),f"{tag}: bold end labels gone")
        ck(not errs,f"{tag}: no page errors {errs[:2]}")
        await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
