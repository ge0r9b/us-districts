# build 1593: QA-081 names stay left-aligned at the same x (52) in every list mode (stacked, split, range stacked, range
# split) and the bars start right after the longest name; QA-080 nationwide at-large rows read 'DE At-large'
# (title 'Delaware at-large'), never 'DE-00'.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
URL="http://localhost:8844/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
Q="""()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,30).map(r=>{ const n=r.querySelector('.nmx'), rn=r.querySelector('b.rn'), bar=r.querySelector('.gbw,.sbw'); const rg=document.createRange(); rg.selectNodeContents(n); const t=rg.getBoundingClientRect(); return {n:n.textContent,t:rn.title,x:t.left,rnR:rn.getBoundingClientRect().right,bl:bar?bar.getBoundingClientRect().left:null} })"""
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W in [390,375,320]:
      ctx=await b.new_context(viewport={'width':W,'height':844},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
      for mode in ["bar","gbar","range gbar","range bar"]:
        if mode=="range gbar": await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll() }"); await pg.wait_for_timeout(4000)
        await setc(pg,mode.split()[-1]); rows=await pg.evaluate(Q)
        xs=[r['x'] for r in rows]; ck(rows and max(abs(x-52) for x in xs)<=1,f"{W} All States {mode}: names left-aligned at x=52",[round(min(xs or [0])),round(max(xs or [0]))])
        if mode!="range bar":
          gap=[r['bl']-r['rnR'] for r in rows if r['bl'] is not None]; ck(gap and max(gap)<=8.5,f"{W} All States {mode}: bars start right after the names (gap {max(gap or [0]):.1f}px)",gap[:4])
      await ctx.close()
      ctx=await b.new_context(viewport={'width':W,'height':844},has_touch=True,is_mobile=True); pg=await ctx.new_page(); pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(700); await pg.evaluate("()=>document.querySelector('.lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(4500)
      await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(500)
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(6000)
      allr=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>[r.querySelector('.nmx').textContent,r.querySelector('b.rn').title])")
      al=[x for x in allr if 'At-large' in x[0]]; bad=[x for x in allr if re.search(r'-0+$',x[0]) or 'district 00' in x[1].lower()]
      ck(len(allr)>=400 and len(al)>=5 and not bad and all(re.fullmatch(r'[A-Z]{2} At-large',x[0]) and ' at-large' in x[1] for x in al),f"{W} US House nationwide: at-large rows 'DE At-large', title '... at-large' ({len(al)} rows)",[len(allr),al[:3],bad[:3]])
      ck(not er,f"{W}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
