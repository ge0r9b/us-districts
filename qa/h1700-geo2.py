# Oct 25 5PM copy of b1620-geo2.py
# hourly ~4PM (1618): QA-113 retest (from h1600-inst2): pick a district type, then geo filter entry (Enter or row tap), close sheet; type must clear and the entered place must show
import asyncio,sys,json,os
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
LT="()=>({on:[...document.querySelectorAll('#lyrRow .lbtn.on')].map(b=>b.dataset.k).join(','),lt:JSON.parse(JSON.stringify(window.__stateSnapshot())).lt})"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; view=sys.argv[3]; out={}; FLD=os.environ.get('FLD','fold')
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    QS=[('Pennsylvania','enter'),('Philadelphia County','row:Philadelphia County, PA'),('Pittsburgh','enter'),('Fulton','row:Fulton County, GA'),('Ohio','row:Ohio')]
    if os.environ.get('ENTER'): QS=[('Pennsylvania','enter'),('Philadelphia County, PA','enter'),('Pittsburgh','enter'),('Fulton County, GA','enter'),('Ohio','enter')]
    if os.environ.get('QS'): QS=[(x,'enter') for x in os.environ['QS'].split('|')]
    for q,how in [x for x in QS if len(sys.argv)<5 or x[0] in sys.argv[4].split(',')]:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      R=out[q]={'how':how}
      if view=='list': await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(2500)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
      await pg.touchscreen.tap(*(await center(pg,'#lyrRow .lbtn[data-k=ushouse]'))); await pg.wait_for_timeout(2500)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1500)
      R['pre']=await pg.evaluate(LT)
      if FLD=='gq':
        await typegq(pg,q); R['body']=await pg.evaluate("document.body.className")
      else:
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1300)
        inp=await pg.evaluate(INP); R['inp']=inp; await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500)
        await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1500)
      R['rows']=await pg.evaluate(SHEET); R['li']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40)).slice(0,5)")
      if how=='enter': await pg.keyboard.press('Enter')
      else:
        xy=await pg.evaluate(VISTXT,how.split(':',1)[1]); R['rowxy']=xy
        if xy: await pg.touchscreen.tap(*xy)
      await pg.wait_for_timeout(5000)
      R['sheet_open']=await pg.evaluate("()=>!document.getElementById('sheet').hidden"); R['sheet']=await pg.evaluate(SHEET); R['lt_open']=await pg.evaluate(LT)
      await safeshot(pg,f"shotsb1620/b1620h17-{eng[:2]}-{W}x{H}-geo2{FLD}{os.environ.get('ENTER','')}{os.environ.get('SUF','')}-{view}-{q.replace(' ','')}-1.png")
      if R['sheet_open'] and FLD!='gq': await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(4000)
      R['closed']={'lt':await pg.evaluate(LT),'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'mp':await pg.evaluate(MP),'rows':(await pg.evaluate(ROWS))[:3]}
      await safeshot(pg,f"shotsb1620/b1620h17-{eng[:2]}-{W}x{H}-geo2{FLD}{os.environ.get('ENTER','')}{os.environ.get('SUF','')}-{view}-{q.replace(' ','')}-2.png")
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(q,json.dumps({k:R[k] for k in ['pre','li','lt_open','closed','sheet','err'] if k in R})[:1500],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1620h1700-geo2{FLD}-{eng}-{W}x{H}-{view}{os.environ.get('ENTER','')}{os.environ.get('SUF','')}.json",'w'),indent=1)
asyncio.run(main())
