# Oct 26 ~7 AM (1622): DC __stTot 2016/2020/2024 + 2024/2020 county data for large counties (ELECTION2024['State|County'] = [D,R,total])
import asyncio,json
from playwright.async_api import async_playwright
from common import *
K=['Arizona|Maricopa County','Illinois|Cook County','Texas|Harris County','Washington|King County','California|Los Angeles County','Florida|Miami-Dade County','Texas|Dallas County','Nevada|Clark County','California|San Diego County','District of Columbia|District of Columbia']
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    r={'build':await pg.evaluate("window.BUILD"),'dc':await pg.evaluate("()=>['2016','2020','2024'].map(y=>window.__stTot('District of Columbia',y))"),
       'cty':await pg.evaluate("K=>{const o={};for(const k of K)o[k]={'2024':window.ELECTION2024[k],'2020':window.ELECTION2020&&window.ELECTION2020[k]};return o}",K)}
    print(json.dumps(r,indent=0)); json.dump(r,open('b1622d26h07-probe.json','w'),indent=1)
    await b.close()
asyncio.run(main())
