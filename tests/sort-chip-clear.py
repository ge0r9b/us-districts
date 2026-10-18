# build 1590 (QA-044): the list sort chip never covers a bar or a value, at any size, in any list mode (stacked, split,
# range), scrolled or not: its line is a header row of its own (rows start below it and scroll clipped under it).
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
HIT="""()=>{ const s=document.getElementById('laSort'); if(getComputedStyle(s).display==='none') return {shown:false}; const c=s.getBoundingClientRect(); const lv=document.getElementById('listView'); const clip=lv.getBoundingClientRect().top+(parseFloat(getComputedStyle(lv).paddingTop)||0)-2;
 const els=[...lv.querySelectorAll('.lvrow.la .sbw, .lvrow.la .sg, .lvrow.la .gbw, .lvrow.la .gbt, .lvrow.la .cbt, .lvrow.la .cbv, .lvrow.la b, .lvrow.la i, .lvrow.la span')].filter(e=>e.offsetParent);
 const bad=[]; for(const e of els){ const r=e.getBoundingClientRect(); if(!r.width||!r.height) continue; const top=Math.max(r.top,clip); if(top>=r.bottom) continue; if(r.left<c.right&&r.right>c.left&&top<c.bottom&&r.bottom>c.top) bad.push([e.className||e.tagName,(e.textContent||'').slice(0,12),Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]); }
 return {shown:true,chip:[c.left,c.top,c.right,c.bottom].map(Math.round),clip:Math.round(clip),bad:bad.slice(0,5),n:els.length} }"""
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      for place in ["All States","Pennsylvania schools"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
        if place!="All States":
          await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type("pennsylvania"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        if place!="All States": await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(4000)
        await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
        for mode in ["bar","gbar","range bar","range gbar"]:
          if mode=="range bar": await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll() }"); await pg.wait_for_timeout(4000)
          await setc(pg,mode.split()[-1])
          for num in ["pct","num"]:
            await pg.evaluate(f"()=>window.__setNum('{num}')"); await pg.wait_for_timeout(1200)
            for sc in [0,13,47]:
              await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={sc}}}"); await pg.wait_for_timeout(300)
              h=await pg.evaluate(HIT)
              ck(h['shown'] and not h['bad'],f"{W} {place} {mode} {num} scroll {sc}: chip clear of every bar and value",h)
            await pg.evaluate("()=>{document.getElementById('listView').scrollTop=0}")
        if W==390 and place=="All States": await pg.screenshot(path="/workspace/sort-chip-clear-390.png")
        ck(not er,f"{W} {place}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
