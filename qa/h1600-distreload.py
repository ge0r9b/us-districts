# Oct 25 ~6AM (1618): reload after picking a state-legislative / US House district row from the list (no time slider)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value||document.getElementById('gq').placeholder,ysl:window.__ysl.get(),list:document.body.classList.contains('listmode')})"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
SNAP="()=>JSON.stringify(window.__stateSnapshot())"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for case in sys.argv[3].split('|'):
      st,k,row,view=case.split(':'); R=out[case]={}
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,st); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(900)
      await pg.touchscreen.tap(*(await center(pg,f'#lyrRow .lbtn[data-k={k}]'))); await pg.wait_for_timeout(4500)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
      if not (await pg.evaluate(HDR))['list']: await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4500)
      F="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.textContent.trim()===t);if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
      if row=='@1': F="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].filter(e=>e.offsetParent)[0];if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,e.textContent.trim()]}"
      await pg.evaluate(F,row); await pg.wait_for_timeout(500); xy=await pg.evaluate(F,row); R['xy']=xy
      if xy: await pg.touchscreen.tap(xy[0],xy[1]); await pg.wait_for_timeout(5000)
      if view=='map' and (await pg.evaluate(HDR))['list']: await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4500)
      R['before']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(SNAP)]
      tg=f"shotsh1600/b1620h16-{eng[:2]}-{W}x{H}-distreload-{st.replace(' ','')}-{k}-{row}-{view}"
      await safeshot(pg,tg+'-before.png'); await pg.wait_for_timeout(1500)
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
      R['after']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(SNAP)]; await safeshot(pg,tg+'-after.png')
      R['ok']=R['before'][0]['crumbs']==R['after'][0]['crumbs'] and R['before'][1]==R['after'][1]
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]
      print(case,'OK' if R['ok'] else 'FAIL',json.dumps(R)[:1800],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1620h1600-distreload-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
