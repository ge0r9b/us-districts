# build 1592 (user): no empty margin between the status bar and the Topic/Search row: the Topic row starts right at the
# safe-area top, the map runs to the very top edge, and nothing sits above the safe-area top (notch / Dynamic Island).
# Checked with no inset and with a simulated 47px / 59px inset (standalone / home-screen), at 390/375/320 WebKit.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
Q="""()=>{ const r=e=>e.getBoundingClientRect(); const bs=document.getElementById('barSearch'), mp=document.getElementById('map'); const vis=[...document.querySelectorAll('.v2bar, .rbtn, #cands .cand, #bSearch, #bGeo, #bLyr')].filter(e=>e.offsetParent&&r(e).width>0&&r(e).height>0);
 return {bar:r(bs).top, map:r(mp).top, minTop:Math.min(...vis.map(e=>r(e).top)), rows:[...document.querySelectorAll('.v2bar')].filter(e=>e.offsetParent).map(e=>[e.id,Math.round(r(e).top),Math.round(r(e).bottom)])} }"""
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      for sat in [0,47,59]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        if sat: await ctx.add_init_script(f"document.addEventListener('DOMContentLoaded',()=>document.documentElement.style.setProperty('--sat','{sat}px'))")
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
        for view in ["map","list"]:
          if view=="list": await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2000)
          q=await pg.evaluate(Q); tag=f"{W} inset {sat} {view}"
          ck(abs(q['bar']-sat)<=0.5,f"{tag}: Topic/Search row starts right at the safe-area top ({q['bar']})",q)
          ck(q['map']<=0.5,f"{tag}: map runs to the top edge",q)
          ck(q['minTop']>=sat-0.5,f"{tag}: nothing above the safe-area top",q)
        if W==390 and sat==0: await pg.screenshot(path="/workspace/top-flush-390.png")
        ck(not er,f"{W} inset {sat}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
