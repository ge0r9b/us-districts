# pass 13: does DC row -> Delaware (state menu) crash the page? Repeats N times, logs page 'crash', heap, errors.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from importlib import import_module
T=import_module('p13-thumbs'.replace('-','_')) if False else None
async def main():
  W,H=int(sys.argv[1]),int(sys.argv[2]); N=int(sys.argv[3]); out=[]
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for i in range(N):
      c,pg,log=await ctx(b,W,H,W<600); crashed=[]; pg.on('crash',lambda *_: crashed.append(1))
      r={'i':i}
      try:
        await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map&&document.getElementById('state').options.length>40",timeout=90000); await pg.wait_for_timeout(3500)
        r['build']=await pg.evaluate('window.BUILD')
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
        await pg.evaluate("()=>{const e=[...document.querySelectorAll('.lvrow')].filter(e=>/^\\s*DC\\b/.test(e.innerText)).pop();e.scrollIntoView();e.click();return 1}"); await pg.wait_for_timeout(3000)
        r['dc']=await pg.evaluate("()=>document.getElementById('crumbs').innerText.replace(/\\n/g,' ')")
        await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Delaware';s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(4000)
        r['de']=await pg.evaluate("()=>[document.getElementById('crumbs').innerText.replace(/\\n/g,' '),document.getElementById('gq').placeholder,document.getElementById('gq').value]")
        r['heap']=await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null")
        r['th']=await pg.evaluate("()=>[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>{const b=e.getBoundingClientRect();return [Math.round(b.left),Math.round(b.top),e.innerText.replace(/\\n/g,' ')]})")
        if i==0: await safeshot(pg,f"../shots/b1579p13-ch-{W}-DE-after-DC.png")
      except Exception as e: r['exc']=str(e)[:160]
      r['crash']=bool(crashed); r['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]
      print(json.dumps(r),flush=True); out.append(r)
      try: await c.close()
      except Exception: pass
  json.dump(out,open(f'b1579p13-crash-{W}.json','w'),indent=1)
asyncio.run(main())
