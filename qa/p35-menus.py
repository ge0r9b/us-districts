# pass 19 (1586): menus are overlays: no dim, pie never shrinks or moves when the chart or district-type menu opens
import asyncio,re,json,sys
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
src=open('p19-new.py').read(); CH=re.search(r'^CH="""(.*?)"""',src,re.M|re.S).group(1).replace('\\\\','\\')
async def main():
  eng=sys.argv[1]; out=[]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in [v for v in VPS if len(sys.argv)<3 or v[0] in sys.argv[2:]]:
      for place in ['US','Alabama']:
        c,pg,log=await ctx(b,W,H,mob,eng); s=tag.replace('iphone','').replace('ipad','')
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(5000)
        if place!='US': await typegq(pg,place); await pg.wait_for_timeout(800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .copts button[data-ch=pie]'))); await pg.wait_for_timeout(2500)
        g0=await pg.evaluate(CH)
        l1=await tap_latency(pg,*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(900); g1=await pg.evaluate(CH); await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-{s}-menus-{place}-lyr.png")
        await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(900); g2=await pg.evaluate(CH)
        l3=await tap_latency(pg,*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900); g3=await pg.evaluate(CH); await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-{s}-menus-{place}-chart.png")
        iss=[]
        for k,g in [('district-type menu open',g1),('district-type menu closed',g2),('chart menu open',g3)]:
          if g['pie']!=g0['pie']: iss.append(f"pie {g0['pie']} -> {g['pie']} with {k}")
          if g['fixedDim']: iss.append(f"{k}: tinted layer {g['fixedDim']}")
        o={'size':tag,'place':place,'pie':g0['pie'],'iss':iss,'lat':[l1,l3],'dim':[g1['dim'],g3['dim']],'err':log['pageerr'][:3]}; out.append(o); print(json.dumps(o),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1614p35-menus-{eng}-{"_".join(sys.argv[2:])}.json','w'),indent=1)
asyncio.run(main())
