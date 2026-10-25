# 1620: town entered from list view (bottom field Enter), no district type: title vs thumbnails vs rows
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for q in sys.argv[3].split('|'):
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(2500)
      await typegq(pg,q); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      R=out[q]={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'rows':(await pg.evaluate(ROWS))[:3],'snap':await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())")}
      tg=f"shotsh1600/b1620h16-{eng[:2]}-{W}x{H}-listtown-{q.replace(' ','').replace(',','')}"
      await safeshot(pg,tg+'-list.png')
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4000)
      R['map']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH)}; await safeshot(pg,tg+'-map.png')
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(6000)
      R['reload']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH)}
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(q,json.dumps(R)[:1500],flush=True); await c.close()
    json.dump(out,open(f"b1620h1600-listtown-{eng}-{W}x{H}.json",'w'),indent=1); await b.close()
asyncio.run(main())
