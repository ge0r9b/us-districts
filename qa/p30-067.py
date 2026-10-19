# pass 27: QA-067 on 1604 in the real UI: geo button > tap the institution field > type queries (real taps + typing)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
ROWS="""()=>[...document.querySelectorAll('#sheet li, #orgSearch li')].filter(l=>l.offsetParent&&l.style.display!=='none').map(l=>(l.classList.contains('orggh')?'## ':'')+((l.querySelector('.nm')||l).textContent||'').trim().replace(/\\s+/g,' ').slice(0,45)).filter(Boolean).slice(0,14)"""
Q=['America','Afrika','Penn','Ohio','Pensylvania','Philadelphia','Calif','USA','uk','Allegheny','Georgia','Amelia']
async def main():
  out={}
  async with async_playwright() as p:
    for eng,W,H in [(a,int(x),int(y)) for a,x,y in [s.split(':') for s in sys.argv[1].split(',')]]:
      b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000); bd=await pg.evaluate("window.BUILD")
      o=out[f'{eng}-{W}x{H}']={'build':bd,'q':{}}
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
      for q in Q:
        xy=await center(pg,'#barGeo .fsq input')
        if xy: await pg.touchscreen.tap(*xy)
        await pg.keyboard.press('Control+A'); await pg.keyboard.press('Meta+A'); await pg.keyboard.press('Backspace')
        v=await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input');return i&&i.value}")
        if v: 
          for _ in range(len(v)): await pg.keyboard.press('Backspace')
        await pg.keyboard.type(q,delay=35); await pg.wait_for_timeout(1400)
        o['q'][q]=await pg.evaluate(ROWS)
        if q in('America','Pensylvania','Afrika','Penn'): await safeshot(pg,f"../shots/b{bd[-4:]}p30-{eng[:2]}-{W}x{H}-inst-{q}.png")
        print(eng,W,H,bd,q,json.dumps(o['q'][q]),flush=True)
      o['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:5]+log['reqfail'][:5]
      await c.close(); await b.close()
  json.dump(out,open(f"b1608p30-067.json",'w'),indent=1)
asyncio.run(main())
