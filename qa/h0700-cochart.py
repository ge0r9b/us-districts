# hourly ~5PM (1618): chart menu (pie/bar/line) + ranges in a county drill at 1024x576 / 320: values in % and #, layout overlap/clip, list sort flip
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('h1500-pa16.py').read().split('async def main')[0].split('from gaps import typegq')[1])
exec(open('p33-flow.py').read().split('ROWS=')[0].split('from common import *')[1])
CT="()=>(document.getElementById('cands')||{innerText:''}).innerText.replace(/\\n/g,' | ').slice(0,500)"
CB="()=>(document.getElementById('chartBox')||{innerText:''}).innerText.replace(/\\n/g,' | ').slice(0,300)"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | ')).slice(0,6)"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; places=sys.argv[3].split('|'); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for pl in places:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      R=out[pl]={'build':await pg.evaluate("window.BUILD")}; tg=pl.split(',')[0].replace(' ','')
      await typegq(pg,pl); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      R['crumbs']=await pg.evaluate("document.getElementById('crumbs').innerText"); R['gq']=await pg.evaluate("document.getElementById('gq').placeholder")
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1000)
      for ch in ['pie','bar','line']:
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        R.setdefault('opts',await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)"))
        R.setdefault('menu_layout',await pg.evaluate(LAYOUT))
        if ch=='pie': await safeshot(pg,f"shotsh0700/b1618h7a-{eng[:2]}-{W}x{H}-cochart-{tg}-menu.png")
        xy=await center(pg,f'#chartBox .copts button[data-ch={ch}]')
        if xy: t=await tap_latency(pg,*xy)
        else: t=None; await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain')))
        await pg.wait_for_timeout(2000)
        for yl,js in [('24','window.__ySetYr(2)'),('16','window.__ySetYr(0)'),('16-20','window.__ySet16(1)'),('20-24','window.__ySelectAll()'),('16-24','window.__ySet16(2)')]:
          await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(2200)
          for mode in ['pct','num']:
            await pg.evaluate("w=>window.__setNum(w)",mode); await pg.wait_for_timeout(1300)
            k=f'{ch}-{yl}-{mode}'; R[k]={'lat':t,'mode':await pg.evaluate("()=>window.chartMode"),'ym':await pg.evaluate("()=>window.__ymode()"),'txt':await pg.evaluate(CT),'cb':await pg.evaluate(CB),'th':await pg.evaluate(TH),'lay':await pg.evaluate(LAYOUT)}
            if mode=='pct' or yl in('24','16-24'): await safeshot(pg,f"shotsh0700/b1618h7a-{eng[:2]}-{W}x{H}-cochart-{tg}-{k}.png")
            print(pl,k,R[k]['mode'],R[k]['ym'],R[k]['txt'][:220],'TH',R[k]['th'],'LAY',R[k]['lay'],flush=True)
      await pg.evaluate("()=>{window.__ySetYr(2);window.__setNum('pct')}"); await pg.wait_for_timeout(2000)
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4500)
      R['list']={'crumbs':await pg.evaluate("document.getElementById('crumbs').innerText"),'rows':await pg.evaluate(ROWS),'lay':await pg.evaluate(LAYOUT)}
      if await center(pg,'#laSort'):
        R['list']['sort_lat']=await tap_latency(pg,*(await center(pg,'#laSort'))); await pg.wait_for_timeout(1800); R['list']['rows_flip']=await pg.evaluate(ROWS)
        await safeshot(pg,f"shotsh0700/b1618h7a-{eng[:2]}-{W}x{H}-cochart-{tg}-list-flip.png")
        await pg.touchscreen.tap(*(await center(pg,'#laSort'))); await pg.wait_for_timeout(1800); R['list']['rows_back']=await pg.evaluate(ROWS)
      print(pl,'list',json.dumps(R['list'])[:1500],flush=True)
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]+[x for x in log['reqfail'] if 'arcgis' not in x][:4]+log['http'][:4]; print(pl,'err',R['err'],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h0700-cochart-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
