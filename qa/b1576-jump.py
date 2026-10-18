# b1576: before/after screenshots for the two thumbnail jumps found in b1576-thumbs.py (list mode DE after DC: dy+30; Blount results->list: dx -8/+8).
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
exec(open('b1576-thumbs.py').read().split('async def boot')[0].split('from cmp import AB')[1])
VISTXT="(t)=>{const L=[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent&&e.innerText);const nm=e=>e.innerText.trim().split('\\n').map(x=>x.replace('›','').trim()).filter(x=>x.length>1)[0]||'';let e=L.filter(e=>nm(e)===t);if(!e.length)return null;const r=e[e.length-1];r.scrollIntoView({block:'nearest'});r.click();return 1}"
POS="()=>[...document.querySelectorAll('img')].filter(i=>/trump|harris/.test(i.src)&&i.offsetParent).map(i=>{const r=i.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top)]})"
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,(W,H) in {'1024x768':(1024,768),'390':(390,844)}.items():
      c,pg,log=await ctx(b,W,H,W<600); R=out[tag]={}
      cdp=await c.new_cdp_session(pg)
      await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map",timeout=90000); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>{const e=[...document.querySelectorAll('.lvrow')].filter(e=>/^\\s*DC\\b/.test(e.innerText)).pop();e.scrollIntoView();e.click();return 1}"); await pg.wait_for_timeout(4000)
      await cdp.send('Emulation.setCPUThrottlingRate',{'rate':6})
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Delaware';s.dispatchEvent(new Event('change',{bubbles:true}));return 1}")
      R['de_before']=await pg.evaluate(POS); await pg.screenshot(path=f'../shots/b1576-jump-{tag}-DEafterDC-before.png')
      await pg.wait_for_timeout(2500); R['de_after']=await pg.evaluate(POS); await pg.screenshot(path=f'../shots/b1576-jump-{tag}-DEafterDC-after.png')
      await cdp.send('Emulation.setCPUThrottlingRate',{'rate':1})
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='';s.dispatchEvent(new Event('change',{bubbles:true}));return 1}"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate(VISTXT,'Alabama'); await pg.wait_for_timeout(5000)
      await pg.evaluate(VISTXT,'Blount County'); await pg.wait_for_timeout(7000)
      R['bl_pre']=await pg.evaluate(POS); await pg.screenshot(path=f'../shots/b1576-jump-{tag}-Blount-results.png')
      await cdp.send('Emulation.setCPUThrottlingRate',{'rate':6})
      await pg.evaluate("()=>{document.getElementById('bGlobe').click();return 1}")
      R['bl_before']=await pg.evaluate(POS); await pg.screenshot(path=f'../shots/b1576-jump-{tag}-Blountlist-before.png')
      await pg.wait_for_timeout(2500); R['bl_after']=await pg.evaluate(POS); await pg.screenshot(path=f'../shots/b1576-jump-{tag}-Blountlist-after.png')
      print(tag,R,flush=True); await c.close()
    await b.close()
  json.dump(out,open('b1576-jump.json','w'),indent=1)
asyncio.run(main())
