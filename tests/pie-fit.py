# build 1585 (user): single-year pie sits right under the slider row (top level with the first thumbnail, within 10px), between the thumbnail column and the floating buttons, fully above the bottom field. WebKit, time row open and closed, '16 and '24.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
G="""()=>{ const v=e=>{ if(!e||!e.offsetParent) return null; const r=e.getBoundingClientRect(); return r.width?r:null }; const s=document.querySelector('.cpanel .cpie1 svg'); const sr=s&&s.getBoundingClientRect();
 const th=[...document.querySelectorAll('#cands img')].filter(e=>!e.closest('.cpanel')).map(v).filter(Boolean).sort((a,b)=>a.top-b.top);
 const bb=document.getElementById('barBottom').getBoundingClientRect(); const bt=[...document.querySelectorAll('button.rbtn')].map(v).filter(r=>r&&r.left>innerWidth/2);
 return sr?{t:sr.top,b:sr.bottom,l:sr.left,r:sr.right,S:sr.width,th:th.length?th[0].top:null,thR:th.length?Math.max(...th.map(r=>r.right)):0,bb:bb.top,btn:bt.filter(r=>r.bottom>sr.top&&r.top<sr.bottom).map(r=>r.left)}:null }"""
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(int(a.split("x")[0]),int(a.split("x")[1])) for a in (sys.argv[1:] or ["390x844","375x667","320x568","1024x768","844x390"])]:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Worcester County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(3500)
      if not await pg.evaluate("()=>document.body.classList.contains('listmode')"): await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2000)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch==='pie'); b&&b.click()}"); await pg.wait_for_timeout(1500)
      for yr in ["'24","'16"]:
        if yr=="'16": await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(4000)
        for tb in ["closed","open"]:
          if (tb=="open")==await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
          g=await pg.evaluate(G); tag=f"{W}x{H} {yr} time {tb}"
          if not g: ck(False,f"{tag}: pie drawn"); continue
          if W==390 and yr=="'16" and tb=="closed": await pg.screenshot(path="/workspace/pie-390-webkit.png",timeout=120000)
          ck(g['th'] is not None and abs(g['t']-g['th'])<=10,f"{tag}: pie top {g['t']:.0f} vs first thumbnail top {g['th']}")
          ck(g['b']<=g['bb'],f"{tag}: pie bottom {g['b']:.0f} above the bottom field {g['bb']:.0f}")
          ck(g['l']>=g['thR'] and all(g['r']<=x for x in g['btn']) and g['r']<=W,f"{tag}: pie {g['l']:.0f}-{g['r']:.0f} between thumbnails (right {g['thR']:.0f}) and buttons {g['btn']} (S={g['S']:.0f})")
      ck(not er,f"{W}: no page errors {er[:2]}")
      await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
