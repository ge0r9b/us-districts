# QA-064/QA-073: state senate / state house / school district picks are instant in big states once the idle warm-up has run
import asyncio,sys,time
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "http://localhost:8844/v2/"
M="async js=>{const t0=performance.now();(0,eval)(js);await new Promise(r=>requestAnimationFrame(()=>setTimeout(r,0)));return performance.now()-t0}"
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for st in ["Texas","California"]:
      pg=await b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL+"?v=%d"%time.time(),wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate(f"()=>{{const s=document.getElementById('state');s.value='{st}';s.onchange&&s.onchange()}}")
      t0=time.time(); warm=[]
      for _ in range(240):
        warm=await pg.evaluate(f"()=>{{const A=window.__aggDbg&&window.__aggDbg().AGG||{{}}; return ['ushouse','senate','statehouse','schools'].filter(k=>A['{st}|'+k+'|2024'])}}")
        if len(warm)==4: break
        await pg.wait_for_timeout(250)
      print("INFO",st,"warmed",warm,"in",round(time.time()-t0,1),"s")
      ck(len(warm)==4,f"{st}: all four district types warmed in idle time ({warm})")
      await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
      for k in ["senate","statehouse","schools"]:
        ms=await pg.evaluate(M,f"document.querySelector('#lyrRow .lbtn[data-k={k}]').click()"); await pg.wait_for_timeout(2500)
        ck(ms<250,f"{st} {k} pick: {ms:.0f} ms tap->paint")
        if not await pg.evaluate("()=>{const e=document.querySelector('#lyrRow .lbtn[data-k=senate]'); return !!(e&&e.getBoundingClientRect().width)}"): await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
      ck(not er,f"{st}: no page errors {er[:2]}")
      await pg.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
