# pass 30 (build 1608): globe toggle list<->map at All States, fresh vs after Back-Back from LA County; map position, heat, focus; drill CA in list then map quickly
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
src=open('p32-back2.py').read(); exec(src[src.index('NMXY='):src.index('async def meas')]); exec(src[src.index('MC="""'):src.index('async def main')])
ST="()=>({crumbs:document.getElementById('crumbs').innerText,list:document.getElementById('listView').offsetParent?1:0,globe:(document.getElementById('bGlobe')||{}).getAttribute&&document.getElementById('bGlobe').getAttribute('aria-label'),thumbs:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,3)})"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in (sys.argv[2] if len(sys.argv)>2 else '390x844').split('x')]; R={'eng':eng}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for sc in ['fresh','backback','tapdc','addr']:
      c,pg,log=await ctx(b,W,H,True,eng); T=R[sc]=[]
      async def note(n): T.append([n,await pg.evaluate(ST),await pg.evaluate(MC)]); print(sc,T[-1],flush=True)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
      await note('load')
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500); await note('allstates_list')
      if sc=='backback':
        await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'CA'))); await pg.wait_for_timeout(3000)
        await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Los Angeles'))); await pg.wait_for_timeout(3000); await note('LA_list')
        await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(2500); await note('back1')
        await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(2500); await note('back2')
      if sc=='tapdc':
        await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'DC'))); await pg.wait_for_timeout(3500); await note('dc_tapped')
      if sc=='addr':
        await pg.touchscreen.tap(*(await center(pg,"#gq"))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
        await pg.keyboard.type("1600 Pennsylvania Ave NW, Washington, DC 20500",delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000); await note('addr_done')
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000); await note('globe1')
      await safeshot(pg,f"../shots/b{R['build'][-4:]}p32-{eng[:2]}-{W}x{H}-globe-{sc}-1.png")
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000); await note('globe2')
      await safeshot(pg,f"../shots/b{R['build'][-4:]}p32-{eng[:2]}-{W}x{H}-globe-{sc}-2.png")
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000); await note('globe3')
      # list -> CA quickly -> map
      if (await pg.evaluate(ST))['list']==0:
        await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000); await note('globe4')
      xy=await pg.evaluate(NMXY,'CA')
      if xy:
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(250)
        R[sc+'_CA_quick']=await tomap(pg,'ca',f"../shots/b{R['build'][-4:]}p32-{eng[:2]}-{W}x{H}-globe-{sc}-CAquick.png"); print('CAquick',R[sc+'_CA_quick'],flush=True)
      R[sc+'_err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:5]
      await c.close()
    await b.close()
  json.dump(R,open(f"b{R['build'][-4:]}p32-globe-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
