import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
CANDS="()=>[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))"
CASES=[("Allegheny County, PA","350 5th Ave, New York, NY 10118"),("Franklin County, OH","1600 Pennsylvania Ave NW, Washington, DC 20500"),("Allegheny County, PA","1600 Pennsylvania Ave NW, Washington, DC 20500"),("Pennsylvania","1600 Pennsylvania Ave NW, Washington, DC 20500"),("Allegheny County, PA","100 Ross St, Pittsburgh, PA 15219")]
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out=[]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for i,(a,q) in enumerate(CASES):
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,a); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000)
      s0=await pg.evaluate(ST); c0=await pg.evaluate(CANDS)
      await typegq(pg,q); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
      s1=await pg.evaluate(ST); c1=await pg.evaluate(CANDS); ll=await pg.evaluate("()=>[+map.getCenter().lat.toFixed(4),+map.getCenter().lng.toFixed(4)]")
      await safeshot(pg,f"../shots/b1582p14-{eng[:2]}-{W}-addr2-{i}.png")
      r=dict(i=i,start=a,q=q,before=[s0['crumb'],s0['ph'],c0],after=[s1['crumb'],s1['ph'],s1['st'],s1['co'],s1['z'],c1,ll],err=log['pageerr']); out.append(r); print(json.dumps(r),flush=True)
      await c.close()
  json.dump(out,open(f'b1582p14-addr2-{eng}-{W}.json','w'),indent=1)
asyncio.run(main())
