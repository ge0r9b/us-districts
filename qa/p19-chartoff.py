# pass 19: turning the chart off (second tap on the chart button while its menu is open) from a single-place chart view
import asyncio,re,json,sys
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
S="()=>{const vis=s=>[...document.querySelectorAll(s)].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'}).length;return {mode:window.chartMode,cls:document.body.className,crumb:(document.getElementById('crumbs')||{}).innerText,rows:vis('#listView .lvrow'),mapvis:(()=>{const m=document.getElementById('map');if(!m)return null;const r=m.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height),getComputedStyle(m).visibility,getComputedStyle(m).display]})(),lv:window.__laInfo&&window.__laInfo().on}}"
async def main():
  eng=sys.argv[1]; url=sys.argv[2] if len(sys.argv)>2 else URL; out=[]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for W,H in ([(390,844)] if len(sys.argv)>2 else [(390,844),(1024,768)]):
     for place in (['US'] if len(sys.argv)>2 else ['US','Alabama']):
      for ch in (['bar'] if len(sys.argv)>2 else ['bar','pie']):
        c,pg,log=await ctx(b,W,H,W<600,eng)
        await pg.goto(url,wait_until="networkidle"); await pg.wait_for_timeout(5000)
        if place!='US': await typegq(pg,place); await pg.wait_for_timeout(800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
        s0=await pg.evaluate(S)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        xy=await center(pg,f'#chartBox .copts button[data-ch={ch}]') or await center(pg,'#chartBox .cmain')
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(2500); s1=await pg.evaluate(S)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        lat=await tap_latency(pg,*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2500); s2=await pg.evaluate(S)
        shot=f"../shots/b1587p19-"+("old1585-" if len(sys.argv)>2 else "")+f"{eng[:2]}-{W}-chartoff-{place}-{ch}.png"; await safeshot(pg,shot)
        o={'W':W,'place':place,'ch':ch,'start':s0,'chart':s1,'off':s2,'lat':lat,'shot':shot,'err':log['pageerr'][:3]}; out.append(o); print(json.dumps(o)[:700],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1587p19-chartoff-{eng}'+('-local' if len(sys.argv)>2 else '')+'.json','w'),indent=1)
asyncio.run(main())
