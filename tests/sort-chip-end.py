# build 1587 (user): the list's sort chip sits at the right end of the bar area, just left of the floating right-hand buttons (never under them), same row and size, no jump. WebKit 390/375/320.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m, flush=True)
  if not c: fails.append(m)
G="""()=>{ const s=document.getElementById('laSort').getBoundingClientRect(); const col=Math.min(...[...document.querySelectorAll('.rbtn')].map(b=>b.getBoundingClientRect()).filter(r=>r.width>0&&r.left>innerWidth-90).map(r=>r.left)); const row=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.offsetParent); const rr=row&&row.getBoundingClientRect();
 return {s:[s.left,s.top,s.width,s.height].map(Math.round), col, row:rr?[Math.round(rr.top),Math.round(rr.bottom)]:null} }"""
REC="""()=>{ window.__fr=[]; const t0=performance.now(); const f=()=>{ const s=document.getElementById('laSort'); const r=s.getBoundingClientRect(); if(r.width&&getComputedStyle(s).display!=='none') __fr.push([Math.round(r.left),Math.round(r.top)]); if(performance.now()-t0<2500) requestAnimationFrame(f) }; requestAnimationFrame(f) }"""
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      for place in ["All States","Pennsylvania schools"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150])); tag=f"{W} {place}"
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if place!="All States":
          await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type("pennsylvania"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        if place!="All States": await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(4000)
        await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate(REC); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3500)
        fr=await pg.evaluate("()=>__fr"); g=await pg.evaluate(G)
        ck(g['s'][2]==34 and g['s'][3]==22,f"{tag}: chip size 34x22 {g['s']}")
        right=g['s'][0]+g['s'][2]
        ck(g['col']-14<=right<=g['col']-2,f"{tag}: chip ends just left of the button column (right {right}, column {g['col']:.0f})")
        ck(len(set(map(tuple,fr)))<=1,f"{tag}: chip never moves once shown {sorted(set(map(tuple,fr)))[:4]}")
        if W==390 and place!="All States": await pg.screenshot(path="/workspace/sort-chip-390.png",timeout=120000)
        ck(not er,f"{tag}: no page errors {er[:2]}"); await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
