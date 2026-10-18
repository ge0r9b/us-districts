# b1575: DC thumbnail size (QA-045). DC is not in the state select; reach it via Geo > All States > District of Columbia row. Then DE to see carry-over.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
exec(open('b1575-thumbs.py').read().split('async def main')[0].split('from cmp import AB')[1])
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,(W,H) in {'1024x768':(1024,768),'390':(390,844)}.items():
      c,pg,log=await ctx(b,W,H,W<600); R=out[tag]={}
      await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map&&document.getElementById('state').options.length>40",timeout=90000); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      R['menu_rows']=await pg.evaluate("()=>[...document.querySelectorAll('li.la-row')].slice(0,4).map(e=>e.innerText.slice(0,40))")
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(300); R['states_early']=await pg.evaluate(M)
      await pg.wait_for_timeout(4000); R['states_late']=await pg.evaluate(M)
      R['dc_click']=await pg.evaluate("()=>{const e=[...document.querySelectorAll('.lvrow')].filter(e=>/^\\s*DC\\b/.test(e.innerText)).pop();if(!e)return null;e.scrollIntoView();e.click();return e.tagName+'.'+e.className}")
      await pg.wait_for_timeout(300); R['DC_early']=await pg.evaluate(M)
      await pg.wait_for_timeout(3500); R['DC_late']=await pg.evaluate(M); R['DC_dom']=await pg.evaluate("()=>{const i=document.querySelector('#crumbs .cic img');return i?i.outerHTML.slice(0,200):document.getElementById('crumbs').innerHTML.slice(0,300)}"); R['DC_vis_imgs']=await pg.evaluate("()=>[...document.querySelectorAll('img')].filter(i=>i.offsetParent&&/cand|pres|photo|portrait/i.test(i.src+i.className+i.parentElement.className)).map(i=>[i.src.split('/').pop().split('?')[0],Math.round(i.getBoundingClientRect().width)])"); await pg.screenshot(path=f'../shots/b1575-thumbs-ch-{tag}-DC.png')
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Delaware';s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(300); R['DE_after_DC_early']=await pg.evaluate(M); await pg.wait_for_timeout(2700); R['DE_after_DC_late']=await pg.evaluate(M)
      await pg.screenshot(path=f'../shots/b1575-thumbs-ch-{tag}-DE-after-DC.png')
      for k,v in R.items(): print(tag,k,json.dumps(v)[:260],flush=True)
      await c.close()
    await b.close()
  json.dump(out,open('b1575-dc.json','w'),indent=1)
asyncio.run(main())
