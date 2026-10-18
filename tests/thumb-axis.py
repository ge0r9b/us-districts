# build 1588 (user): the thumbnail column is centred on the same axis as the topic seal and institution icon above it, in every view, level and year (within 1px). WebKit 390/375/320.
import asyncio,sys
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m, flush=True)
  if not c: fails.append(m)
Q="""()=>{ const c=r=>r.left+r.width/2; const im=[...document.querySelectorAll('#cands .cand img, #cands img.dmt, #laCands img')].filter(i=>i.offsetParent&&i.getBoundingClientRect().width>0&&i.getBoundingClientRect().left<innerWidth/2).map(i=>c(i.getBoundingClientRect()));
 const ic=document.querySelector('#crumbs .cic'); const v=document.getElementById('vtitle'); const vb=getComputedStyle(v,'::before'); const vr=v.getBoundingClientRect();
 const seal=vb&&vb.content&&vb.content!=='none'&&vb.width!=='auto'?vr.left+parseFloat(vb.marginLeft||0)+parseFloat(vb.left||0)*0+parseFloat(vb.width)/2:null;
 return {th:im.map(x=>Math.round(x*10)/10), ic:ic?Math.round(c(ic.getBoundingClientRect())*10)/10:null, seal:seal&&Math.round(seal*10)/10} }"""
async def setc(pg,k):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(450)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset&&b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(1500)
async def yr(pg,i):
  if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
  d=await pg.evaluate("()=>[...document.querySelectorAll('#ysl .tk i')].map(i=>{const r=i.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]})")
  await pg.touchscreen.tap(*d[i]); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      async def chk(tag):
        g=await pg.evaluate(Q); ok=g['th'] and g['ic'] is not None and all(abs(x-g['ic'])<=1 for x in g['th'])
        ck(ok,f"{W} {tag}: thumbnails {g['th']} on the icon axis {g['ic']} (seal {g['seal']})")
      await chk("US map '24")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500); await chk("US list")
      await setc(pg,"bar"); await chk("US bar"); await setc(pg,"pie"); await chk("US pie")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(700); await pg.evaluate("()=>document.querySelector('.lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(4500)
      await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(500); await chk("US House map '24")
      for i,y in [(0,"'16"),(1,"'20"),(2,"'24")]: await yr(pg,i); await chk(f"US House map {y}")
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000); await chk("PA US House map")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500); await chk("PA list")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500); await chk("PA map again")
      await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Allegheny County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(4000)
      for i,y in [(0,"'16"),(2,"'24")]: await yr(pg,i); await chk(f"Allegheny map {y}")
      ck(not er,f"{W}: no page errors {er[:2]}"); await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
