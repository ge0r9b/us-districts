import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
ROWXY="""n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim().startsWith(n)});if(!r)return null;r.scrollIntoView({block:'center'});const q=(r.querySelector('.nmx')||r).getBoundingClientRect();return [q.left+q.width/2,q.top+q.height/2]}"""
async def main():
  eng=sys.argv[1]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,390,844,True,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    for n in ['PA','Philadelphia']:
      xy=await pg.evaluate(ROWXY,n); await pg.wait_for_timeout(500); l=await tap_latency(pg,*xy); await pg.wait_for_timeout(7000)
      i=await pg.evaluate("()=>window.__laInfo()"); print(n,l,i['lv'],len(i['order']),[x for x in i['order'] if 'ockledge' in x[0]],i['order'][:3],flush=True)
    await pg.screenshot(path=f'../shots/b1593p21-{eng[:2]}-390-philadelphia-list.png')
    print(await pg.evaluate('window.BUILD'),log['pageerr'][:2]); await b.close()
asyncio.run(main())
