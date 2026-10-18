import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('p16-wkback.py').read().split('async def main')[0].split('from common import *')[1])
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for run in range(2):
      c,pg,log=await ctx(b,390,844,True,'chromium'); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      R={}
      R['geo']=await tap_latency(pg,*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
      R['allstates']=await tap_latency(pg,*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
      await pg.wait_for_timeout(600); R['drill_PA']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
      R['drill_county']=await tap_latency(pg,*(await pg.evaluate(ROW))); await pg.wait_for_timeout(6000)
      R['drill_town']=await tap_latency(pg,*(await pg.evaluate(ROW))); await pg.wait_for_timeout(6000)
      for i in range(3): R[f'back{i+1}']=await tap_latency(pg,*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3000)
      R['globe_to_map']=await tap_latency(pg,*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
      out[run]=R; print(run,R,log['pageerr'][:2],flush=True); await c.close()
  json.dump(out,open('b1584p16-lat-chromium-390.json','w'),indent=1)
asyncio.run(main())
