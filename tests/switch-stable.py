# build 1586: QA-060 icons never move on map<->list switches (every frame); QA-070 the clock button never leaves its spot when All States opens with the time row open. Chromium + WebKit.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
REC="""()=>{ window.__fr=[]; const t0=performance.now(); const f=()=>{ const b=document.getElementById('bTime').getBoundingClientRect(); const i=[...document.querySelectorAll('#cands .cand img')].find(x=>x.offsetParent), r=i&&i.getBoundingClientRect();
  __fr.push([Math.round(performance.now()-t0),b.width?Math.round(b.left):null,b.width?Math.round(b.top):null,r?Math.round(r.left):null]); if(performance.now()-t0<1400) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""
async def main():
  async with async_playwright() as p:
    for eng in ["chromium","webkit"]:
      b=await getattr(p,eng).launch()
      for W,H in [(390,844),(375,667),(320,568),(1024,768)]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150])); tag=f"{eng} {W}"
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000)
        for step in ["map>list","list>map","map>list again"]:
          await pg.evaluate(REC); await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1600)
          xs=[x[3] for x in await pg.evaluate("()=>__fr") if x[3] is not None]
          ck(xs and max(xs)-min(xs)<=1,f"{tag} QA-060 {step}: icon x steady every frame {sorted(set(xs))}")
        ctx2=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); await ctx.close(); pg=await ctx2.new_page(); pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
        r0=await pg.evaluate("()=>{const b=document.getElementById('bTime').getBoundingClientRect(); return [Math.round(b.left),Math.round(b.top)]}")
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.wait_for_timeout(800)
        await pg.evaluate(REC); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(1800)
        fr=[x for x in await pg.evaluate("()=>__fr") if x[1] is not None]
        bad=[x for x in fr[1:] if abs(x[1]-r0[0])>1 or abs(x[2]-r0[1])>6]
        ck(fr and not bad,f"{tag} QA-070: clock button stays at {r0} while All States opens (time row open) {bad[:3]}")
        ck(not er,f"{tag}: no page errors {er[:2]}"); await ctx2.close()
      await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
