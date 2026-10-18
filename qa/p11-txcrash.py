import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); o={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for stn,k in (('Texas','senate'),('California','statehouse')):
      c,pg,log=await ctx(b,W,H,W<600,eng); crashed=[]; pg.on('crash',lambda *_: crashed.append(1))
      await pg.goto(URL,wait_until="load",timeout=180000); await pg.wait_for_timeout(8000)
      await typegq(pg,stn); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(6000)
      m0=await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null")
      xy=await center(pg,'#bLyr'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1500)
      xy=await center(pg,f'#lyrRow .lbtn[data-k={k}]'); lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(8000)
      try:
        m1=await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null"); s=await pg.evaluate(ST)
        await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{W}-{k}-{stn}-solo.png")
      except Exception as e: m1=s=str(e)[:80]
      o[stn+':'+k]=dict(lat=lat,heapMB=[m0,m1],st=s,crashed=bool(crashed),err=log['pageerr'][:3])
      print(stn,k,o[stn+':'+k],flush=True)
      try: await c.close()
      except: pass
  json.dump(o,open(f'b1576p11-txcrash-{eng}-{W}.json','w'),indent=1)
asyncio.run(main())
