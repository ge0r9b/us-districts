# pass 28: QA-087 on 1605: compare the address result from a list view with tapping the DC row in All States
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
src=open('p28-addr.py').read()
exec(src[src.index('NMXY='):src.index('ADDR=')])
ST2="""()=>{const r=[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent);const dc=r.find(x=>x.innerText.trim().startsWith('DC')||x.innerText.includes('At-large'));
 const lv=document.getElementById('listView');
 return {back:[...document.querySelectorAll('button,div,span')].filter(e=>e.offsetParent&&/back/i.test((e.id||'')+' '+(e.getAttribute('aria-label')||''))).map(e=>e.id||e.getAttribute('aria-label')).slice(0,4),
 dc:dc?{txt:dc.innerText.replace(/\\n/g,' | '),cls:dc.className,y:Math.round(dc.getBoundingClientRect().top),bg:getComputedStyle(dc).backgroundColor}:null,scroll:lv?lv.scrollTop:null,nrows:r.length}}"""
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
async def main():
  eng=sys.argv[1]; W,H=390,844; R={'eng':eng}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for sc in ['tapdc','addr']:
      c,pg,log=await ctx(b,W,H,True,eng)
      try:
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
        await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        if sc=='tapdc':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'DC'))); await pg.wait_for_timeout(4000)
        else:
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3500)
          await pg.touchscreen.tap(*(await center(pg,"#gq"))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
          await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
        R[sc]={'st':await pg.evaluate(ST),'st2':await pg.evaluate(ST2),'err':log['pageerr']+[x for x in log['console'] if x.startswith('error')]}
        await pg.screenshot(path=f"../shots/b{R['build'][-4:]}p28-{eng[:2]}-390-dc-{sc}.png")
        # then tap Back chevron if present: what does it go to?
        print(sc,json.dumps(R[sc]),flush=True)
      except Exception as e: R[sc]={'EXC':str(e)[:300]}; print('EXC',sc,e,flush=True)
      await c.close()
    await b.close()
  json.dump(R,open(f"b{R.get('build','0000')[-4:]}p28-dc-{eng}-390.json",'w'),indent=1)
asyncio.run(main())
