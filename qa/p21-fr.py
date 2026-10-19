# pass 21: first list row settles 2 px after a drill-in from All States? sample every frame
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
FR="""(ms)=>new Promise(res=>{const out=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const r=[...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent);const s=document.getElementById('laSort');const q=r&&r.getBoundingClientRect();const c=s&&s.getBoundingClientRect();out.push([Math.round(t),q?Math.round(q.top):null,q?(r.innerText||'').split('\\n')[0].slice(0,14):'',c&&c.width?Math.round(c.top):null]);if(t<ms)requestAnimationFrame(f);else res(out)};requestAnimationFrame(f)})"""
async def main():
  eng=sys.argv[1]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for W,H in [(1024,768),(390,844)]:
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      for rep,st in enumerate(['MA','CA','MA','WY']):
        xy=await pg.evaluate("n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n});r.scrollIntoView({block:'center'});const q=r.querySelector('.nmx').getBoundingClientRect();return [q.left+q.width/2,q.top+q.height/2]}",st)
        await pg.wait_for_timeout(600)
        samp=asyncio.ensure_future(pg.evaluate(FR,1500)); await pg.touchscreen.tap(*xy); fr=await samp
        seq=[]
        for x in fr:
          if not seq or seq[-1][1:]!=x[1:]: seq.append(x)
        k=f"{W} {st}#{rep}"; out[k]=seq; print(eng,k,seq[:8],flush=True)
        await pg.wait_for_timeout(1500)
        await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3500)
      await c.close()
    await b.close()
  json.dump(out,open(f'b1593p21-fr-{eng}.json','w'),indent=1)
asyncio.run(main())
