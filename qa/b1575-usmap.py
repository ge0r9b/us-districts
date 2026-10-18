# b1575: US-level map colours in '16 ranges vs '20>'24 (pixel sample at state centres)
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
PTS={'CO':[39.0,-105.5],'KS':[38.5,-98.4],'IL':[40.0,-89.2],'TX':[31.3,-99.3],'FL':[28.3,-81.7],'UT':[39.3,-111.7],'GA':[32.7,-83.4]}
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__map"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
    await pg.evaluate("()=>{window.__map.setView([38.5,-96],4,{animate:false});return 1}"); await pg.wait_for_timeout(2500)
    xy=await pg.evaluate("P=>{const o={};for(const[k,v] of Object.entries(P)){const q=window.__map.latLngToContainerPoint(v);o[k]=[Math.round(q.x),Math.round(q.y)]}return o}",PTS)
    from PIL import Image
    out={}
    for name,js,w in [('20-24',"()=>{window.__ySelectAll();return 1}",6000),('16-24',"()=>{window.__ySet16(2);return 1}",12000),('16-20',"()=>{window.__ySet16(1);return 1}",12000),('2016',"()=>{window.__ySet16(0);return 1}",10000)]:
      await pg.evaluate(js); await pg.wait_for_timeout(w); f=f'../shots/b1575-usmap-ch-1024x768-{name}.png'; await pg.screenshot(path=f)
      im=Image.open(f).convert('RGB'); out[name]={k:im.getpixel((v[0]*2,v[1]*2)) for k,v in xy.items()}
      out[name]['ysl']=await pg.evaluate("()=>window.__ysl.get()")
    for k,v in out.items(): print(k,v)
    print('err',log['pageerr'])
    await c.close(); await b.close()
asyncio.run(main())
