import asyncio,json
from playwright.async_api import async_playwright
from common import *
from cmp import AB
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(9000)
    app=await pg.evaluate("names=>{const o={};for(const [a,n] of Object.entries(names)){o[a]={};for(const y of ['2016','2020','2024']){try{o[a][y]=window.__stTot(n,y)}catch(e){o[a][y]=String(e)}}};return o}",AB)
    await c.close(); await b.close()
  json.dump(app,open('b1574-tot.json','w'))
  f16=json.load(open('fec16.json')); f24=json.load(open('fec24.json')); f20=json.load(open('fec20.json'))
  for a in ['VT','ND','WY','MD','AL','PA']:
    v=app[a]; print(a,'2016 app',v['2016'][:3],'fec',f16[a]['C'],f16[a]['T'],f16[a]['TOT'],'| 2024 app',v['2024'][:3],'fec',f24['HARRIS'][a],f24['TRUMP'][a],f24['TOTAL_VOTES'][a],'| 2020 app',v['2020'][:3],'fec',f20['BIDEN'][a],f20['TRUMP'][a],f20['TOTAL_VOTES'][a])
asyncio.run(main())
