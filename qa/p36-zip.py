# pass 36: address/ZIP searches that fall back to a ZIP (no precise match): title / numbers vs field
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('p35-addr2.py').read().split('ADDR0=')[0].split('from common import *')[1])
Q=[('stpaul','75 Rev Dr Martin Luther King Jr Blvd, St Paul, MN 55155'),('zip55155','55155'),('zip90210','90210'),('fakeduluth','1 Nonexistent Rd, Duluth, MN 55802'),('mpls','600 Nicollet Mall, Minneapolis, MN 55402'),('zip30334','30334')]
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; only=sys.argv[3].split(',') if len(sys.argv)>3 else None; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for k,a in Q:
      if only and k not in only: continue
      c,pg,log=await ctx(b,W,H,W<600,eng); R=out[k]={'q':a}
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      await pg.touchscreen.tap(*(await center(pg,'#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()")
      await pg.keyboard.type(a,delay=15); await pg.wait_for_timeout(4000)
      R['sugg']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.textContent.trim().slice(0,60)).slice(0,4)")
      await pg.keyboard.press('Enter'); await pg.wait_for_timeout(9000)
      R['res']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(POP),await pg.evaluate(MP),await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),await pg.evaluate("()=>document.getElementById('gq').value")]
      await safeshot(pg,f"shots36/b1615p36-{eng[:2]}-{W}x{H}-zip-{k}.png")
      await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
      R['reload']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(MP)]
      await safeshot(pg,f"shots36/b1615p36-{eng[:2]}-{W}x{H}-zip-{k}-reload.png")
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:5]
      print(k,json.dumps(R)[:1600],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1615p36-zip-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
