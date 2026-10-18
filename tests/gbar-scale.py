# build 1590 (QA-078 HIGH): a split-bar list uses ONE shared scale across the whole list: every bar's length is
# proportional to its value (range: the change; # mode: votes; % mode: share), so lengths compare across rows.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
BARS="""()=>[...document.querySelectorAll('#listView .lvrow.la .gbt')].filter(e=>e.offsetParent).map(e=>[parseFloat(e.querySelector('i').style.width), e.querySelector('b').textContent])"""
def num(t):
  t=t.replace('\u2212','-').replace('%','').replace('+','').strip(); m=1
  if t.endswith('M'): m=1e6; t=t[:-1]
  elif t.endswith('K'): m=1e3; t=t[:-1]
  try: return abs(float(t)*m)
  except: return None
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W in ([int(a) for a in sys.argv[1:]] or [390,375,320]):
      ctx=await b.new_context(viewport={'width':W,'height':844},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
      await setc(pg,"gbar")
      for yr in ["'24","'16","range '20-'24","range '16-'24"]:
        if yr=="'16": await pg.evaluate("()=>window.__ySetYr(0)"); await pg.wait_for_timeout(4000)
        if yr=="'24": await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(3000)
        if yr=="range '20-'24": await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(4000)
        if yr=="range '16-'24": await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(5000)
        for nm in ["num","pct"]:
          await pg.evaluate(f"()=>window.__setNum('{nm}')"); await pg.wait_for_timeout(1500)
          bars=await pg.evaluate(BARS); r=[(w/num(t)) for w,t in bars if num(t) and w>4 and (nm=="num" or num(t)>=2)]
          ok=len(r)>=20 and max(r)/min(r)<1.12
          ck(ok,f"{W} {yr} {nm}: split bars on one shared scale ({len(r)} bars, ratio spread {max(r)/min(r) if r else 0:.3f})",bars[:8])
          if W==390 and yr.startswith("range '20") and nm=="num": await pg.screenshot(path="/workspace/gbar-scale-390.png")
      ck(not er,f"{W}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
