import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
EP="()=>{const out=[];for(const [x,y] of [[210,177],[205,170],[215,185]]){const e=document.elementFromPoint(x,y);out.push(e?[e.tagName,e.id,(e.className||'').toString().slice(0,40),e.parentElement&&e.parentElement.id,(e.closest('[id]')||{}).id,(e.dataset&&e.dataset.ch)||'']:null)}const cb=document.getElementById('chartBox');return {ep:out,open:cb&&cb.classList.contains('open'),cls:cb&&cb.className,opts:[...document.querySelectorAll('#chartBox .copts button')].map(b=>{const r=b.getBoundingClientRect();const cs=getComputedStyle(b);return [b.dataset.ch,Math.round(r.left),Math.round(r.top),Math.round(r.width),cs.opacity,cs.visibility,!!b.offsetParent]})}}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    async def t(sel,w=1200):
      xy=await center(pg,sel); 
      if not xy: print('NOVIS',sel); return
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(w)
    async def st(n):
      r=await pg.evaluate(EP); print(n,json.dumps(r),flush=True); await safeshot(pg,f"shotsb1621/b1621h20-{eng[:2]}-{W}x{H}-cb-{n}.png")
    await typegq(pg,'Oregon'); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    await t('#bTime',1500); await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(2500); await st('1-range')
    await t('#chartBox .cmain',1000); await st('2-menuopen')
    await t('#chartBox .copts button[data-ch=line]',2500); await st('3-line')
    await t('#bNum',1200); await st('4-numsheet')
    opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
    if opt: await pg.touchscreen.tap(*opt); await pg.wait_for_timeout(2000)
    await st('5-num')
    await t('#chartBox .cmain',1000); await st('6-menuopen2')
    await t('#chartBox .copts button[data-ch=line]',2500); await st('7-line2')
    await t('#chartBox .cmain',1000); await st('8-menuopen3')
    await t('#chartBox .cmain',1500); await st('9-menuclose3')
    print('ERR',log['pageerr'],[x for x in log['console'] if x.startswith('error')][:5])
asyncio.run(main())
