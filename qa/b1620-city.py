# hourly ~5PM (1618): QA-115 breadth: ambiguous city names, fresh load (no type), bottom field (#gq) or geo-filter sheet (#bGeo) + Enter
import asyncio,sys,json,os
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; FLD=sys.argv[3]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for q0 in sys.argv[4].split('|'):
      q,_,how=q0.partition('@')
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      R=out[q0]={}
      try:
        if FLD=='gq': await typegq(pg,q)
        else:
          await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1300)
          inp=await pg.evaluate(INP); await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500)
          await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(2000)
        R['li']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,45)).slice(0,5)")
        if how=='row':
          xy=await pg.evaluate("()=>{const l=[...document.querySelectorAll('li')].filter(e=>e.offsetParent&&e.innerText.trim()&&!/^[A-Z ]+$/.test(e.innerText.trim()))[0];if(!l)return null;const r=l.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,l.innerText.slice(0,40)]}")
          R['rowtap']=xy
          if xy: await pg.touchscreen.tap(xy[0],xy[1])
        else: await pg.keyboard.press('Enter')
        await pg.wait_for_timeout(int(os.environ.get('WT','6000')))
        if FLD!='gq' and await pg.evaluate("()=>!document.getElementById('sheet').hidden"):
          R['sheet']=await pg.evaluate(SHEET); await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(3500)
        R.update({'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'mp':await pg.evaluate(MP),'gqv':await pg.evaluate("document.getElementById('gq').value"),'sel':await pg.evaluate("()=>{const s=window.__stateSnapshot();return {sel:s.sel,st:s.st,co:s.co,lt:s.lt}}")})
      except Exception as e: R['EXC']=str(e)[:200]
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]+log['reqfail'][:4]+log['http'][:4]
      await safeshot(pg,f"shotsh1600/b1620h16-{eng[:2]}-{W}x{H}-city{FLD}-{q0.replace(' ','').replace(',','').replace('@','-')}.png")
      print(q0,json.dumps(R)[:900],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1620h1600-city{FLD}-{eng}-{W}x{H}{os.environ.get('SUF','')}.json",'w'),indent=1)
asyncio.run(main())
