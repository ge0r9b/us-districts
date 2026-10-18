import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
FIND="(ab)=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()===ab});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left,q.top+q.height/2,q.width]}"
EFP="([x,y])=>{const e=document.elementFromPoint(x,y);return e?(e.tagName+'.'+e.className+' #'+e.id+' < '+(e.parentElement&&e.parentElement.className)).slice(0,120):null}"
INFO="()=>{const i=window.__laInfo&&window.__laInfo();return i&&[i.lv,document.getElementById('crumbs')&&document.getElementById('crumbs').innerText.replace(/\\n/g,' '),window.chartMode,document.body.className.slice(0,120)]}"
async def main():
  eng=sys.argv[1]; out=[]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for mode,dx in [('chart-off',60),('chart-off',150),('bar',60),('bar',150)]:
      c,pg,log=await ctx(b,390,844,True,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      if mode=='bar':
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(800)
        await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2000)
      before=await pg.evaluate(INFO)
      r=await pg.evaluate(FIND,'PA'); await pg.wait_for_timeout(600); r=await pg.evaluate(FIND,'PA')
      x,y=r[0]+dx,r[1]; efp=await pg.evaluate(EFP,[x,y])
      await pg.touchscreen.tap(x,y); await pg.wait_for_timeout(4000)
      after=await pg.evaluate(INFO); await safeshot(pg,f"../shots/b1585p18-{eng[:2]}-390-drillPA-{mode}-{dx}.png")
      o={'mode':mode,'dx':dx,'before':before,'efp':efp,'after':after,'err':log['pageerr'][:2]}; print(json.dumps(o),flush=True); out.append(o); await c.close()
    await b.close()
  json.dump(out,open(f'b1585p18-wkdrill-{eng}.json','w'),indent=1)
asyncio.run(main())
