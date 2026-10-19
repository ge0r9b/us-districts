# new: bottom-field (geo filter) Enter on bare city names, fresh load (no district type)
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
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      await typegq(pg,q); li=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40)).slice(0,4)")
      await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000)
      R=out[q]={'li':li,'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'mp':await pg.evaluate(MP),'gqv':await pg.evaluate("document.getElementById('gq').value")}
      await safeshot(pg,f"shotsh1600/b1618h-{eng[:2]}-{W}x{H}-town-{q.replace(' ','').replace(',','')}.png")
      print(q,json.dumps(R)[:700],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h1600-town-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
