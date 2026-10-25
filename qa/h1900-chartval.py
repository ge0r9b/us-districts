# hourly 3PM (1618): bar / line chart values (#cands) vs __stTot (official certified) for a few states, % and #
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('h1500-pa16.py').read().split('async def main')[0].split('from gaps import typegq')[1])
CT="()=>(document.getElementById('cands')||{innerText:''}).innerText.replace(/\\n/g,' | ').slice(0,500)"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; states=sys.argv[3].split(','); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for stn in states:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      R=out[stn]={'build':await pg.evaluate("window.BUILD")}
      await typegq(pg,stn); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      R['tot']=await pg.evaluate("n=>{const o={};for(const y of ['2016','2020','2024'])o[y]=window.__stTot(n,y);return o}",stn)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1000)
      for ch in ['bar','line']:
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        xy=await center(pg,f'#chartBox .copts button[data-ch={ch}]')
        if xy: await pg.touchscreen.tap(*xy)
        else: await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain')))
        await pg.wait_for_timeout(2000)
        for yl,js in [('24','window.__ySetYr(2)'),('16','window.__ySetYr(0)'),('20-24','window.__ySelectAll()'),('16-24','window.__ySet16(2)')]:
          await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(2200)
          for mode in ['pct','num']:
            await pg.evaluate("w=>window.__setNum(w)",mode); await pg.wait_for_timeout(1500)
            k=f'{ch}-{yl}-{mode}'; R[k]={'mode':await pg.evaluate("()=>window.chartMode"),'ysl':await pg.evaluate("()=>window.__ysl.get()"),'g':await pg.evaluate(G),'txt':await pg.evaluate(CT)}
            await safeshot(pg,f"shotsb1621/b1621h19-{eng[:2]}-{W}x{H}-chartval-{stn.replace(' ','')}-{k}.png")
            print(stn,k,R[k]['mode'],R[k]['ysl'],R[k]['txt'][:300],flush=True)
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]; print(stn,'tot',json.dumps(R['tot']),'err',R['err'],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1621h1900-chartval-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
