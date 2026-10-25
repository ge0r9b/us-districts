# Oct 25 7AM (1618): Burlington city (Chittenden, VT) precinct list contains "South Burlington City"
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
HDR="()=>({crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value||document.getElementById('gq').placeholder,list:document.body.classList.contains('listmode')})"
NM="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    async def tapn(t):
      await pg.evaluate(NM,t); await pg.wait_for_timeout(400); xy=await pg.evaluate(NM,t)
      if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
      return xy
    await typegq(pg,'Vermont'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    out['tapCh']=await tapn('Chittenden')
    out['county']=[await pg.evaluate(HDR),await pg.evaluate(TH),(await pg.evaluate(ROWS))[:5]]
    out['tapBur']=await tapn('Burlington city')
    out['bur']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(ROWS)]
    await safeshot(pg,f'shotsh0700/b1618h7a-{eng[:2]}-{W}x{H}-vtbur-list.png')
    await pg.evaluate("()=>window.__setNum&&window.__setNum('num')"); await pg.wait_for_timeout(1500)
    out['bur_num']=[await pg.evaluate(TH),await pg.evaluate(ROWS)]
    await safeshot(pg,f'shotsh0700/b1618h7a-{eng[:2]}-{W}x{H}-vtbur-list-num.png')
    out['tapSB']=await tapn('South Burlington')
    out['sb']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(ROWS)]
    await safeshot(pg,f'shotsh0700/b1618h7a-{eng[:2]}-{W}x{H}-vtbur-tapSB.png')
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
    print(json.dumps(out,indent=0)); await b.close()
asyncio.run(main())
