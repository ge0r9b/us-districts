import asyncio,sys,json,time
from playwright.async_api import async_playwright
from common import *
exec(open('p16-wkback.py').read().split('async def main')[0].split('from common import *')[1])
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for second in ['touch','jsclick']:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
      await pg.wait_for_timeout(600); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
      for i in range(2): await pg.touchscreen.tap(*(await pg.evaluate(ROW))); await pg.wait_for_timeout(6000)
      seq=[('start',await pg.evaluate(LV))]
      await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3000); seq.append(('after1',await pg.evaluate(LV)))
      t0=time.time()
      if second=='touch': await pg.touchscreen.tap(*(await center(pg,'#bBack')))
      else: await pg.evaluate("()=>document.getElementById('bBack').click()")
      tl=[]
      for _ in range(60):
        tl.append((round(time.time()-t0,2),await pg.evaluate(LV))); await pg.wait_for_timeout(100)
      ch=[x for i,x in enumerate(tl) if i==0 or x[1]!=tl[i-1][1]]
      out[second]={'seq':seq,'changes':ch,'err':log['pageerr'][:2]}; print(eng,W,second,seq,ch,log['pageerr'][:2],flush=True)
      await safeshot(pg,f"../shots/b1584p16-{eng[:2]}-{W}-back2-{second}.png"); await c.close()
  json.dump(out,open(f'b1584p16-back2-{eng}-{W}.json','w'),indent=1)
asyncio.run(main())
