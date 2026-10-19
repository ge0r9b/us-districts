# pass 25: range chart (2020>2024) with the time row closed vs open: what bubble appears after a thumbnail tap, per frame for 2.5 s
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
FR="""(ms)=>new Promise(res=>{const o=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const v=JSON.stringify(['iconBub','partyBub'].map(id=>{const e=document.getElementById(id);if(!e)return null;const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return [id,e.textContent,[r.left,r.top,r.right,r.bottom].map(Math.round),cs.opacity,cs.visibility]}));if(!o.length||o[o.length-1][1]!==v)o.push([Math.round(t),v]);if(t<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"""
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for closed in [True,False]:
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(900)
      await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
      if closed: await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(900)
      await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
      await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2500)
      th=await pg.evaluate("()=>[...document.querySelectorAll('#cands img.dmt, #cands .dmoc')].filter(e=>e.offsetWidth).map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom].map(Math.round)})")
      key='closed' if closed else 'open'; out[key]={'thumbs':th,'mode':await pg.evaluate('()=>window.chartMode'),'taps':[]}
      for i,t in enumerate(th[:4]):
        s=asyncio.ensure_future(pg.evaluate(FR,2500)); await pg.wait_for_timeout(30)
        await pg.touchscreen.tap((t[0]+t[2])/2,(t[1]+t[3])/2); await pg.wait_for_timeout(350)
        await safeshot(pg,f'../shots/b1599p26-{eng[:2]}-{W}x{H}-rangebub-{key}-{i}.png')
        fr=await s; out[key]['taps'].append([t,fr]); print(eng,W,key,i,t,[(a,json.loads(v)) for a,v in fr][:5],flush=True); await pg.wait_for_timeout(2500)
      out[key]['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; out[key]['build']=await pg.evaluate('window.BUILD'); await c.close()
    await b.close()
  json.dump(out,open(f'b1599p26-rangebub-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
