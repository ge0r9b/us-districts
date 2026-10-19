# pass 23: per-frame first 3 list rows (top/height) on drill-in and Back, bar vs split bar list
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
FR="""(ms)=>new Promise(res=>{const o=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const rows=[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).slice(0,3).map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.top),Math.round(r.height)]});const nm=(document.querySelector('#listView .lvrow .nmx')||{}).textContent||'';const v=JSON.stringify([rows,nm]);if(!o.length||o[o.length-1][1]!==v)o.push([Math.round(t),v]);if(t<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"""
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    async def nmxy(t):
      return await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'nearest'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",t)
    async def run(name,xyf,shot=False):
      xy=await xyf()
      if not xy: out[name]='target missing'; print(name,'missing'); return
      await pg.wait_for_timeout(300)
      samp=asyncio.ensure_future(pg.evaluate(FR,1200)); await pg.wait_for_timeout(20)
      await pg.touchscreen.tap(*xy)
      if shot: await pg.wait_for_timeout(190); await safeshot(pg,f'../shots/b1596p24-{eng[:2]}-{W}-rowfr-{name}-mid.png')
      fr=await samp; out[name]=fr; print(eng,W,name,[(t,json.loads(v)) for t,v in fr][:8],flush=True); await pg.wait_for_timeout(2500)
      if shot: await safeshot(pg,f'../shots/b1596p24-{eng[:2]}-{W}-rowfr-{name}-end.png')
    back=lambda: center(pg,'#bBack')
    for mode in ['bar','gbar']:
      if mode=='gbar':
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .copts button[data-ch=gbar]'))); await pg.wait_for_timeout(3000)
      for rep in range(2):
        await run(f'{mode}-drillMA-{rep}',lambda: nmxy('MA'),shot=(rep==0))
        await run(f'{mode}-drillWorc-{rep}',lambda: nmxy('Worcester'))
        await run(f'{mode}-back1-{rep}',back)
        await run(f'{mode}-back2-{rep}',back,shot=(rep==0))
    out['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; out['build']=await pg.evaluate('window.BUILD'); print('err',out['err'])
    await c.close(); await b.close()
  json.dump(out,open(f'b1596p24-rowfr-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
