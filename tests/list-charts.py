# build 1585 (user): lists of places never show pies; the chart button on a list offers only the totaled bar and the split (grouped) bar (+ line for a range); a single place keeps its pie for one year.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
MENU="""async()=>{ const m=document.querySelector('[aria-label=Chart]'); m.click(); await new Promise(r=>setTimeout(r,400)); const o=[m.dataset.ch,...[...document.querySelectorAll('#chartBox .copts button')].map(b=>b.dataset.ch)]; document.getElementById('chartDim').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); return o }"""
ROWS="""()=>{ const R=[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent); return {n:R.length,pie:R.filter(r=>r.querySelector('.pwr, svg circle')).length,sb:R.filter(r=>r.querySelector('.sbw:not(.nd)')).length,gb:R.filter(r=>r.querySelectorAll('.gbt').length>=2).length,mode:window.chartMode} }"""
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def openlist(pg,name):
  if name!="All States":
    await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type("massachusetts"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  if name!="All States": await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(4000)
  await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
async def main():
  async with async_playwright() as p:
    for eng,W,H in [("webkit",390,844),("chromium",1024,768)][:int(sys.argv[1]) if len(sys.argv)>1 else 2]:
      b=await getattr(p,eng).launch(); ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      for name in (["MA school districts"] if "ma" in sys.argv else ["All States","MA school districts"]):
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); pg=await ctx.new_page(); pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
        if name=="All States": await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500); await setc(pg,"pie")
        await openlist(pg,name); first=name=="All States"
        for yr in ["'24","'16","range"]:
          if yr=="'16": await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(4000)
          if yr=="range": await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll() }"); await pg.wait_for_timeout(4000)
          tag=f"{eng} {W} {name} {yr}"
          r=await pg.evaluate(ROWS)
          if first: ck(r['mode']=="bar" and r['pie']==0 and r['sb']>=3,f"{tag}: a pie chosen on a place falls to the totaled bar on the list {r}"); first=False
          o=await pg.evaluate(MENU); ck("pie" not in o and "bar" in o and "gbar" in o and (("line" in o)==(yr=="range")),f"{tag}: chart menu {o} "+str(await pg.evaluate("()=>[window.__ymRaw&&__ymRaw(), window.__y16, window.__y16hi, document.getElementById('yslider').value]")))
          await setc(pg,"bar"); r=await pg.evaluate(ROWS); ck(r['n']>=3 and r['pie']==0 and r['sb']>=r['n']-1,f"{tag}: totaled bar rows, no pies {r}")
          if W==390 and name.startswith("MA") and yr=="'16": await pg.screenshot(path="/workspace/list-bar-390.png",timeout=120000)
          await setc(pg,"gbar"); r=await pg.evaluate(ROWS); ck(r['n']>=3 and r['pie']==0 and r['gb']>=r['n']-1,f"{tag}: split bar rows (one bar per candidate), no pies {r}")
          if W==390 and name.startswith("MA") and yr=="'16": await pg.screenshot(path="/workspace/list-gbar-390.png",timeout=120000)
          await setc(pg,"bar")
      ck(not er,f"{eng}: no page errors {er[:2]}")
      await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
