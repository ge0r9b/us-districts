# build 1589 (CRITICAL, user): "This map should not be only red". Every level in 2016/2020/2024 colours by that year's
# margin: blue where the Democrat won (Philadelphia, Manhattan, DC), red where the Republican won (rural central PA).
# Live 1587: the '16 US House layer fell through to the 2020>24 shift colours (all red) and PA's own districts were gray.
import asyncio,sys,json,io
from PIL import Image
from playwright.async_api import async_playwright
URL="https://ge0r9b.github.io/us-districts/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
PTS={"Philadelphia":(39.985,-75.15,"D"),"Brooklyn":(40.65,-73.95,"D"),"DC":(38.905,-77.02,"D"),"rural PA":(40.75,-77.6,"R")}
async def main():
  W_=[int(a) for a in sys.argv[1:] if a.isdigit()] or [390,375,320]
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W in W_:
      for st,typ in [("",None),("","ushouse"),("Pennsylvania",None),("Pennsylvania","ushouse"),("Pennsylvania","senate"),("Pennsylvania","statehouse")]:
        ctx=await b.new_context(viewport={'width':W,'height':844},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if st: await pg.evaluate(f"()=>{{const s=document.getElementById('state');s.value={json.dumps(st)};s.onchange&&s.onchange()}}"); await pg.wait_for_timeout(3500)
        if typ:
          await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(700); await pg.evaluate(f"()=>document.querySelector('.lbtn[data-k={typ}]').click()"); await pg.wait_for_timeout(4500)
          await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(600)
        for yi,yr in [(0,"2016"),(1,"2020"),(2,"2024")]:
          await pg.evaluate(f"()=>window.__ySetYr({yi})"); await pg.wait_for_timeout(5000 if yi==0 else 3000)
          pts=PTS if not st else {k:v for k,v in PTS.items() if k in ("Philadelphia","rural PA")}
          res={}
          for nm,(la,lo,win) in pts.items():
            x,y,hit=await pg.evaluate(f"()=>{{ map.setView([{la},{lo}],9,{{animate:false}}); const q=map.latLngToContainerPoint([{la},{lo}]); const r=map.getContainer().getBoundingClientRect(); const X=q.x+r.left,Y=q.y+r.top; const e=document.elementFromPoint(X,Y); return [X,Y,!!(e&&e.closest('.leaflet-container')&&!e.closest('.leaflet-control'))]}}")
            await pg.wait_for_timeout(1800)
            img=Image.open(io.BytesIO(await pg.screenshot())).convert("RGB"); sc=img.width/W
            px=[img.getpixel((int((x+dx)*sc),int((y+dy)*sc))) for dx in (-6,0,6) for dy in (-6,0,6)]
            r=sorted(c[0] for c in px)[4]; g=sorted(c[1] for c in px)[4]; bl=sorted(c[2] for c in px)[4]
            got="D" if bl>r+25 else "R" if r>bl+25 else "?"
            res[nm]=[got,win,(r,g,bl),int(x),int(y),hit]
          tag=f"{W} {st or 'US'} {typ or 'map'} {yr}"
          ck(all(v[0]==v[1] for v in res.values()),f"{tag}: blue where D won, red where R won "+", ".join(f"{k}={v[0]}" for k,v in res.items()),res)
          if yr=="2016" and W==390: await pg.screenshot(path=f"../shots/b1592p21-webkit-otest-col16-{(st or 'US')[:2]}-{typ or 'map'}.png")
        ck(not er,f"{W} {st or 'US'} {typ or 'map'}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
