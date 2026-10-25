# Oct 25 ~6AM (1618): pie in a state-legislative district (map view): does the pie option show a pie?
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
HDR="()=>({crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),mode:window.chartMode,lt:window.__stateSnapshot().lt,la:window.__stateSnapshot().la,lap:window.__stateSnapshot().lap})"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for st,k in [x.split(':') for x in sys.argv[3].split('|')]:
      R=out[st+k]={}; c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
      await typegq(pg,st); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      async def T(sel,w): await pg.touchscreen.tap(*(await center(pg,sel))); await pg.wait_for_timeout(w)
      if k!='none':
        await T('#bLyr',900); await T(f'#lyrRow .lbtn[data-k={k}]',4500)
        if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await T('#bLyr',800)
        await T('#bGlobe',4500)
        xy=await pg.evaluate("()=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].filter(e=>e.offsetParent)[0];const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
        if (await pg.evaluate(HDR))['list']: await T('#bGlobe',4500)
      R['a']=[await pg.evaluate(HDR),await pg.evaluate(TH)]
      await T('#chartBox .cmain',1000); R['menu']=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)")
      tg=f"shotsh1600/b1620h16-{eng[:2]}-{W}x{H}-dpie-{st}-{k}"; await safeshot(pg,tg+'-menu.png')
      await T('#chartBox .copts button[data-ch=pie]',3000); R['b']=[await pg.evaluate(HDR),await pg.evaluate(TH)]; await safeshot(pg,tg+'-pie.png')
      print(st,k,json.dumps(R),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1620h1600-dpie-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
