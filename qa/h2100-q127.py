# Oct 25 5PM: QA-127 / QA-094 quick check via app __townsIn after loading the state
import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True,'chromium'); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    for st,cns in [('Virginia',['Arlington County','Henrico County','Fairfax County']),('Maryland',['Howard County'])]:
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000)
      for cn in cns:
        r=await pg.evaluate("([s,c])=>{try{const T=window.__townsIn(s,c)||[];return [T.length,T.slice(0,6).map(t=>t[2])]}catch(e){return 'ERR '+e}}",[st,cn]); print(st,cn,r,flush=True)
    print('build',await pg.evaluate('window.BUILD'),'err',log['pageerr'][:3]); await b.close()
asyncio.run(main())
