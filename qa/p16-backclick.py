import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('p16-wkback.py').read().split('async def main')[0].split('from common import *')[1])
async def drill(pg):
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
    await pg.wait_for_timeout(600); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(*(await pg.evaluate(ROW))); await pg.wait_for_timeout(6000)
async def main():
  eng=sys.argv[1]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for how in ['touch','mouse','enter','jsclick']:
      c,pg,log=await ctx(b,1024,768,False,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await drill(pg); before=await pg.evaluate(LV); xy=await center(pg,'#bBack')
      if how=='touch': await pg.touchscreen.tap(*xy)
      elif how=='mouse': await pg.mouse.click(*xy)
      elif how=='enter': await pg.focus('#bBack'); await pg.keyboard.press('Enter')
      else: await pg.evaluate("()=>document.getElementById('bBack').click()")
      await pg.wait_for_timeout(3000); after=await pg.evaluate(LV)
      out[how]=[before,after,log['pageerr'][:2]]; print(eng,how,before,'->',after,log['pageerr'][:2],flush=True)
      if how=='mouse': await safeshot(pg,f"../shots/b1584p16-{eng[:2]}-1024-back-mouse.png")
      await c.close()
  out['build']='202610181584'; json.dump(out,open(f'b1584p16-backclick-{eng}.json','w'),indent=1)
asyncio.run(main())
