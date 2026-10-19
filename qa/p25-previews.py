# pass 25: sanity load of design previews (not v2, not v3) at 390x844 Chromium touch: loads, no console errors, data shows
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for nm in ['shadows','compact']:
      c,pg,log=await ctx(b,390,844,True,'chromium'); u=f'https://ge0r9b.github.io/us-districts/previews/{nm}/'
      r=await pg.goto(u,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      info=await pg.evaluate("()=>({build:window.BUILD,title:document.title,robots:(document.querySelector('meta[name=robots]')||{}).content,txt:document.body.innerText.slice(0,400),cands:[...document.querySelectorAll('#cands .cand')].map(e=>(e.getAttribute('aria-label')||'')+' '+((e.querySelector('.cpt')||{}).textContent||'')).slice(0,4),paths:document.querySelectorAll('path').length})")
      await safeshot(pg,f'../shots/b1597p25-ch-390-preview-{nm}.png')
      # open the All States list too
      xy=await center(pg,'#bGeo')
      if xy:
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200); xy=await center(pg,'li.la-row')
        if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(4000)
        info['rows']=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | '))")
        await safeshot(pg,f'../shots/b1597p25-ch-390-preview-{nm}-list.png')
      info['status']=r.status if r else None; info['log']=log; out[nm]=info; print(nm,json.dumps(info)[:1500],flush=True); await c.close()
    await b.close()
  json.dump(out,open('b1597p25-previews-chromium-390x844.json','w'),indent=1)
asyncio.run(main())
