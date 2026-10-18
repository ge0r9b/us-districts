# build 1586 (user): a menu opens as an overlay: opening/closing the chart menu or the district-type menu never resizes, moves or dims the content (pie, bars, list rows). WebKit 390/375/320.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m, flush=True)
  if not c: fails.append(m)
R="""sel=>{const e=document.querySelector(sel); if(!e) return null; const r=e.getBoundingClientRect(); return [r.left,r.top,r.width,r.height].map(x=>Math.round(x*10)/10)}"""
DIM="""()=>{ const d=document.getElementById('chartDim'); const c=getComputedStyle(d); const m=/rgba?\\(([^)]*)\\)/.exec(c.backgroundColor); const a=m?(m[1].split(',')[3]===undefined?1:+m[1].split(',')[3]):0; return {a:+c.opacity*a, filt:[...document.querySelectorAll('#map, #listView, #cands')].map(e=>getComputedStyle(e).filter+getComputedStyle(e).opacity).join(' ')} }"""
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset&&b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(1800)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500)
      views=[("pie",".cpanel svg",None),("bar",".cpanel .sebr .sebt",None),("list",".lvrow.la",None)]
      for v,sel,_ in views:
        if v=="list":
          await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000); await setc(pg,"bar")
        else: await setc(pg,v)
        r0=await pg.evaluate(R,sel)
        for mn,op,cl in [("chart menu","()=>document.querySelector('[aria-label=Chart]').click()","()=>document.getElementById('chartDim').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true}))"),
                         ("district-type menu","()=>document.getElementById('bLyr').click()","()=>document.getElementById('bLyr').click()")]:
          if not await pg.evaluate("()=>!!document.getElementById('bLyr')&&!!document.getElementById('bLyr').offsetParent") and mn.startswith("district"): continue
          await pg.evaluate(op); await pg.wait_for_timeout(450)
          r1=await pg.evaluate(R,sel); d=await pg.evaluate(DIM)
          if W==390 and v=="pie" and mn=="chart menu": await pg.screenshot(path="/workspace/menu-open-pie-390.png",timeout=120000)
          await pg.evaluate(cl); await pg.wait_for_timeout(450); r2=await pg.evaluate(R,sel)
          ck(r0 and r0==r1==r2,f"{W} {v}: {mn} open/close leaves the content rect unchanged {r0} {r1} {r2}")
          ck(d['a']<0.01,f"{W} {v}: {mn} open: no dim {d}")
      ck(not er,f"{W}: no page errors {er[:2]}"); await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
