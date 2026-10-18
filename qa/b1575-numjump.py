import asyncio,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); out=[]
    for run in range(3):
      c,pg,log=await ctx(b,1024,576,False); await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4000)
      for i in range(4):
        await pg.evaluate("()=>{window.__cls=0;window.__shifts=[];window.__cp=[];const f=()=>{const e=document.getElementById('laCands');if(e){const r=e.getBoundingClientRect();window.__cp.push(Math.round(r.top)+','+Math.round(r.height))} if(window.__cp.length<120)requestAnimationFrame(f)};f()}")
        xy=await center(pg,'#bNum'); lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(2000)
        r=await pg.evaluate("()=>({cls:window.__cls,sh:window.__shifts,cp:[...new Set(window.__cp)],nm:window.__numMode&&window.__numMode()})"); r['lat']=lat; r['run']=run
        out.append(r); print(json.dumps(r)[:300],flush=True)
        if any(s['v']>0.05 for s in r['sh']): await safeshot(pg,f'../shots/b1575-ch-1024x576-numjump-r{run}-{i}.png')
      await c.close()
    await b.close()
asyncio.run(main())
