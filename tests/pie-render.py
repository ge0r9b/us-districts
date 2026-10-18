# build 1586 (live 1585 report: PA '16 pie empty): the single-place pie always renders (slices, nonzero size, on screen) for US, PA (time row open and closed) and a county in '16, '20, '24, after slider taps and after reload. WebKit 390/375/320.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
P="""()=>{const s=document.querySelector('#cands > .cpanel svg'); if(!s) return null; const r=s.getBoundingClientRect(); const ps=[...s.querySelectorAll('path,circle')].filter(x=>x.getBoundingClientRect().width>2).length;
 const cx=r.left+r.width/2, cy=r.top+r.height/2; const hit=document.elementFromPoint(cx+r.width*0.2,cy); return {w:r.width,t:r.top,b:r.bottom,l:r.left,r:r.right,ps,vis:!!(hit&&s.contains(hit)),H:innerHeight,W:innerWidth}}"""
async def tapyr(pg,i):
  if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1200)
  d=await pg.evaluate("()=>[...document.querySelectorAll('#ysl .tk i')].map(i=>{const r=i.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]})")
  await pg.touchscreen.tap(*d[i]); await pg.wait_for_timeout(3500)
async def check(pg,tag):
  g=None
  for _ in range(3):
    g=await pg.evaluate(P)
    if g and g['ps']>=2: break
    await pg.wait_for_timeout(800)
  ck(g and g['w']>=80 and g['ps']>=2 and g['vis'] and g['t']>=0 and g['b']<=g['H'] and g['l']>=0 and g['r']<=g['W'],f"{tag}: pie drawn {g}")
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch==='pie'); b&&b.click()}"); await pg.wait_for_timeout(2500)
      for place in ["US","Pennsylvania","Allegheny County"]:
        if place=="Pennsylvania": await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000)
        if place=="Allegheny County": await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Allegheny County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(4000)
        for i,yr in [(0,"'16"),(1,"'20"),(2,"'24")]:
          await tapyr(pg,i); await check(pg,f"{W} {place} {yr} time open")
          if place=="Pennsylvania":
            await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500); await check(pg,f"{W} {place} {yr} time closed")
        await tapyr(pg,0)
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(12000); await check(pg,f"{W} Allegheny '16 after reload")
      ck(not er,f"{W}: no page errors {er[:2]}"); await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
