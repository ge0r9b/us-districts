# hourly 3PM (1618), from p38-inst2: institution field Enter / row tap, then close the sheet: title vs numbers vs field
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    QS=[('Georgia','enter'),('ohio','enter'),('Fulton','row:Fulton County, GA'),('Wayne','row:Wayne County, MI'),('North Carolina','enter'),('FOLD','fold:Georgia'),('Erie','row:Erie County, PA')]
    for q,how in [x for x in QS if len(sys.argv)<4 or x[0] in sys.argv[3].split(',')]:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      R=out[q]={}
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1300)
      if q!='FOLD':
        inp=await pg.evaluate(INP); await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500)
        await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1500)
      R['icon']=await pg.evaluate("()=>{const i=[...document.querySelectorAll('#barGeo img, #crumbs img')].filter(e=>e.offsetParent).map(e=>e.getAttribute('src'));return i}")
      R['rows']=await pg.evaluate(SHEET)
      if how=='enter': await pg.keyboard.press('Enter')
      else:
        xy=await pg.evaluate(VISTXT,how.split(':',1)[1]); R['rowxy']=xy
        if xy: await tap_latency(pg,*xy)
      await pg.wait_for_timeout(5000)
      R['sheet_open']=await pg.evaluate("()=>!document.getElementById('sheet').hidden"); R['sheet']=await pg.evaluate(SHEET)
      R['crumbs_open']=await pg.evaluate("()=>document.getElementById('crumbs').innerText.replace(/\\n/g,' > ')")
      await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-inst2-{q.replace(' ','')}-1.png")
      if R['sheet_open']: await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(4000)
      R['closed']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'mp':await pg.evaluate(MP),'snap':await pg.evaluate(SNAP),'rows':(await pg.evaluate(ROWS))[:3]}
      await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-inst2-{q.replace(' ','')}-2.png")
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(q,json.dumps(R)[:1800],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h1700-inst2-{eng}-{W}x{H}-{sys.argv[3] if len(sys.argv)>3 else 'all'}.json",'w'),indent=1)
asyncio.run(main())
