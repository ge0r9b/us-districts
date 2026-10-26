import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ALLROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).slice(0,6).map(r=>r.innerText.replace(/\\n/g,' | '))"
LV="()=>{const v=document.getElementById('listView');return v?[!!v.offsetParent,v.innerText.slice(0,120)]:null}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    async def t(sel,w): xy=await center(pg,sel); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(w)
    for st in sys.argv[3].split(','):
      await typegq(pg,st); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      s0=await pg.evaluate("()=>window.__stateSnapshot()")
      await t('#bGlobe',4000); a=[await pg.evaluate(ALLROWS),await pg.evaluate(LV)]; await safeshot(pg,f"shotsb1621/b1621h20-{eng[:2]}-{W}x{H}-alp-{st.replace(' ','')}-notype-list.png")
      await t('#bGlobe',3000); await t('#bLyr',900); await t('#lyrRow .lbtn[data-k=ushouse]',4500)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await t('#bLyr',700)
      s1=await pg.evaluate("()=>window.__stateSnapshot()"); await safeshot(pg,f"shotsb1621/b1621h20-{eng[:2]}-{W}x{H}-alp-{st.replace(' ','')}-ush-map.png")
      await t('#bGlobe',4500); bb=[await pg.evaluate(ALLROWS),await pg.evaluate(LV),await pg.evaluate("()=>document.getElementById('crumbs').innerText")]; await safeshot(pg,f"shotsb1621/b1621h20-{eng[:2]}-{W}x{H}-alp-{st.replace(' ','')}-ush-list.png")
      print(st,json.dumps({'snap0':s0,'notype':a,'snap1':s1,'ush':bb})[:1500],flush=True)
      await t('#bGlobe',3000); await t('#bLyr',900); await t('#lyrRow .lbtn[data-k=ushouse]',3000)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await t('#bLyr',700)
    print('ERR',log['pageerr'],[x for x in log['console'] if x.startswith('error')][:5])
asyncio.run(main())
