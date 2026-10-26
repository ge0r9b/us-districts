# Oct 26 ~10 AM (1623): QA-091 recheck (WebKit 390x844 touch): PA > Philadelphia townships list, DC address + Enter in the bottom field, then saved state + reload position. Plus QA-100 data peek (Kings vs Brooklyn).
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
import os
URL=os.environ.get("QAURL",URL)
from gaps import typegq
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
SN="()=>{const s=window.__stateSnapshot();return {crumbs:document.getElementById('crumbs').innerText,st:s.st,co:s.co,ll:s.ll,z:s.z,vw:s.vw,la:s.la,ls:localStorage.getItem('usd.state'),th:[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))}}"
async def main():
  eng=sys.argv[1] if len(sys.argv)>1 else 'webkit'; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,390,844,True,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for lvl in ['PA','Philadelphia']:
      xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    out['phl']=await pg.evaluate(SN)
    await typegq(pg,'1600 Pennsylvania Ave NW, Washington, DC 20500'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000)
    out['dc']=await pg.evaluate(SN); await safeshot(pg,'shotsb1623/d26h10-'+eng[:2]+os.environ.get('TAG','')+'-390x844-q091-dc.png')
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
    out['reload']=await pg.evaluate(SN); await safeshot(pg,'shotsb1623/d26h10-'+eng[:2]+os.environ.get('TAG','')+'-390x844-q091-reload.png')
    out['q100']=await pg.evaluate("()=>[ELECTION2024['New York|Kings County'],Object.keys(ELECTION2024).filter(k=>k.startsWith('New York|')).length]")
    out['err']=[log['pageerr'],[x for x in log['console'] if x.startswith('error')][:5]]
    print(json.dumps(out,indent=1)); json.dump(out,open(f'b1623d26h10-q091-{eng}{os.environ.get("TAG","")}.json','w'),indent=1); await b.close()
asyncio.run(main())
