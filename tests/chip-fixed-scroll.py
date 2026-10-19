# build 1595 (QA-083, no-jump rule): the floating sort chip and back chevron stay at the same place at every scroll stop
# (short drags, longer scrolls, back to the top), phones and wide.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300])); (None if c else F.append(m))
G="()=>{ const s=document.getElementById('laSort').getBoundingClientRect(), b=document.getElementById('bBack').getBoundingClientRect(); return [Math.round(s.left*2)/2,Math.round(s.top*2)/2,Math.round(b.left*2)/2,Math.round(b.top*2)/2] }"
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568),(1280,800)]:
      for place in ["All States","Pennsylvania"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
        if place=="Pennsylvania": await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/^(PA|Pennsylvania)$/.test(r.querySelector('.nmx').textContent)).click()"); await pg.wait_for_timeout(6000)
        g0=await pg.evaluate(G); seen=[]
        for sc in [3,6,12,25,60,140,40,8,0]:
          await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={sc}}}"); await pg.wait_for_timeout(700); seen.append([sc,await pg.evaluate(G)])
        bad=[x for x in seen if x[1]!=g0]
        ck(not bad,f"{W} {place}: chip and chevron fixed at every scroll stop {g0}",bad[:4])
        ck(not er,f"{W} {place}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
