# build 1594 (user, replaces 1590's header band): list rows start right under the slider row (no empty band); the sort chip
# and back chevron float over the top of the list; at rest the chip may overlap bar fill but never a name, number label or
# value, in any list mode (stacked, split, range) and size (phones and wide 1024/1280/1600).
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
HIT="""()=>{ const s=document.getElementById('laSort'); if(getComputedStyle(s).display==='none') return {shown:false}; const c=s.getBoundingClientRect(); const lv=document.getElementById('listView'); const clip=lv.getBoundingClientRect().top; const r1=lv.querySelector('.lvrow.la'); const band=r1?r1.getBoundingClientRect().top-lv.getBoundingClientRect().top:0;
 const els=[...lv.querySelectorAll('.lvrow.la b, .lvrow.la em, .lvrow.la .cbv, .lvrow.la .net, .lvrow.la .nmx')].filter(e=>e.offsetParent);
 const bad=[]; for(const e of els){ const r=e.getBoundingClientRect(); if(!r.width||!r.height||!(e.textContent||'').trim()) continue; const top=Math.max(r.top,clip); if(top>=r.bottom) continue; if(r.left<c.right&&r.right>c.left&&top<c.bottom&&r.bottom>c.top) bad.push([e.className||e.tagName,(e.textContent||'').slice(0,12),Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]); }
 return {shown:true,band,chip:[c.left,c.top,c.right,c.bottom].map(Math.round),clip:Math.round(clip),bad:bad.slice(0,5),n:els.length} }"""
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568),(1024,768),(1280,800),(1600,900)]:
      for place in ["All States","Pennsylvania schools"]:
        ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=W<800,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
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
              await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={sc}}}"); await pg.wait_for_timeout(450)
              h=await pg.evaluate(HIT)
              ck(h['shown'] and not h['bad'],f"{W} {place} {mode} {num} scroll {sc}: chip never covers a name, number label or value",h)
              if sc==0: ck(h.get('band',99)<=17,f"{W} {place} {mode} {num}: rows start right under the slider row (no header band, {h.get('band')}px)",h)
            await pg.evaluate("()=>{document.getElementById('listView').scrollTop=0}")
        if W==390 and place=="All States": await pg.screenshot(path="/workspace/sort-chip-clear-390.png")
        ck(not er,f"{W} {place}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
