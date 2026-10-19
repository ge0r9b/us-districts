# hourly ~5PM: county entered three ways, then globe to the list: does the list show the county's rows?
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | ')).slice(0,4)"
ST="()=>({crumbs:document.getElementById('crumbs').innerText,gq:document.getElementById('gq').placeholder,list:document.body.classList.contains('listmode'),n:document.querySelectorAll('#listView .lvrow.la').length,lv:window.__laInfo().on?window.__laInfo().lv:'-',snap:window.__stateSnapshot()})"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for path in sys.argv[3].split(','):
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      R=out[path]={}
      if path=='gq': await typegq(pg,'Franklin County, OH'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      elif path=='gqrow':
        await typegq(pg,'Franklin County, OH'); xy=await pg.evaluate(VISTXT,'Franklin County, OH'); R['xy']=xy; await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(6000)
      elif path=='bgeo':
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1300)
        inp=await pg.evaluate(INP); await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500); await pg.keyboard.type('Franklin',delay=30); await pg.wait_for_timeout(1800)
        xy=await pg.evaluate(VISTXT,'Franklin County, OH'); R['xy']=xy; await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
        if await pg.evaluate("()=>!document.getElementById('sheet').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(3500)
      elif path=='state':
        await typegq(pg,'Ohio'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        R['statelist']=await pg.evaluate(ST)
        xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",'Franklin'); await pg.wait_for_timeout(400)
        xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",'Franklin')
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
        R['drill']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS)}
        await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4500)
      R['map']={'st':await pg.evaluate(ST),'th':await pg.evaluate(TH),'mp':await pg.evaluate(MP)}
      await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-coglobe-{path}-map.png")
      R['lat_globe']=await tap_latency(pg,*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(5000)
      R['list']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS),'th':await pg.evaluate(TH)}
      await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-coglobe-{path}-list.png")
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(12000)
      R['reload']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS)}
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(path,json.dumps(R),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h1700-coglobe-{eng}-{W}x{H}-{sys.argv[3]}.json",'w'),indent=1)
asyncio.run(main())
