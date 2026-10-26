import asyncio,json
from playwright.async_api import async_playwright
from common import *
CERT={'Pennsylvania':(3423042,3543308),'Rhode Island':(285156,214406),'Vermont':(235791,119395),'Massachusetts':(2126518,1251303),'Michigan':(2736533,2816636),'New Jersey':(2220713,1968215)}
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL+'?cb=1622t',wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000); out={'build':await pg.evaluate("window.BUILD")}
    for n,(d,r) in CERT.items():
      v=await pg.evaluate("([n,y])=>window.__stTot(n,y)",[n,'2024'])
      out[n]={'app':v,'cert':[d,r],'match':bool(v) and v[0]==d and v[1]==r}; print(n,out[n],flush=True)
    out['err']=log['pageerr']; json.dump(out,open('b1622x-tot.json','w'),indent=1); await b.close()
asyncio.run(main())
