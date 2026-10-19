# build 1588 (user): a list whose header names the district type (US House, state senate, state house) shows only the
# district number per row ('9', leading zeros stripped consistently; DC / at-large seats 'At-large'); the bars start in
# the freed space right next to the icon column. Named entities (school districts, counties) keep their names.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
URL="https://ge0r9b.github.io/us-districts/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
ROWS="""()=>{ const th=[...document.querySelectorAll('#laCands .lact, #cands .cand')].filter(b=>b.offsetParent).map(b=>b.getBoundingClientRect().right); const R=[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent); return {thR:th.length?Math.max(...th):null, rows:R.slice(0,60).map(r=>{ const n=r.querySelector('.nmx'); const bar=r.querySelector('.sbw,.gbw,.cbars'); const rg=document.createRange(); rg.selectNodeContents(n); return {n:n.textContent, nl:rg.getBoundingClientRect().left, nr:rg.getBoundingClientRect().right, bl:bar?bar.getBoundingClientRect().left:null, t:r.querySelector('b.rn').title} })} }"""
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def openl(b,W,typ,st,yr):
  ctx=await b.new_context(viewport={'width':W,'height':844},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
  await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
  if typ:
    await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(700); await pg.evaluate(f"()=>document.querySelector('.lbtn[data-k={typ}]').click()"); await pg.wait_for_timeout(4500)
    await pg.evaluate("()=>{const b=document.getElementById('bLyr'); if(document.body.classList.contains('lyropen')||!document.getElementById('lyrRow').hidden) b.click()}"); await pg.wait_for_timeout(500)
  await pg.evaluate(f"()=>{{const s=document.getElementById('state');s.value={json.dumps(st)};s.onchange&&s.onchange()}}"); await pg.wait_for_timeout(4500)
  if yr is not None: await pg.evaluate(f"()=>window.__ySetYr({yr})"); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(5000)
  return ctx,pg,er
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W in ([int(a) for a in sys.argv[1:]] or [390,375,320]):
      for typ,st,yr,named in [("ushouse","Texas",0,False),("ushouse","Texas",2,False),("ushouse","Pennsylvania",2,False),("senate","Pennsylvania",2,False),("statehouse","Pennsylvania",2,False),("ushouse","Alaska",2,False),("ushouse","Wyoming",2,False),("schools","Massachusetts",2,True)]:
        ctx,pg,er=await openl(b,W,typ,st,yr); tag=f"{W} {typ} {st} y{yr}"
        for ch in ["bar","gbar"]:
          await setc(pg,ch); r=await pg.evaluate(ROWS); rows=r['rows']
          if not rows: ck(False,f"{tag} {ch}: rows listed",r); continue
          ns=[x['n'] for x in rows]
          if named: ck(all(not re.fullmatch(r"\d+",n) for n in ns),f"{tag} {ch}: named entities keep their names",ns[:5]); continue
          ok=all(re.fullmatch(r"[1-9]\d*|At-large",n) for n in ns)
          ck(ok and not any(n.lower().startswith("district") for n in ns),f"{tag} {ch}: rows show only the number (no 'District', no leading zero)",ns[:8])
          if st in ("Alaska","Wyoming"): ck(ns==["At-large"],f"{tag} {ch}: the single seat reads 'At-large'",ns)
          ck(all('istrict' in x['t'] or 'At' in x['t'] or 'at-large' in x['t'].lower() for x in rows),f"{tag} {ch}: the title keeps the full name",[x['t'] for x in rows[:3]])
          gap=[round(x['bl']-r['thR'],1) for x in rows if x['bl'] is not None and r['thR']]
          wn=max(x['nr']-x['nl'] for x in rows)
          ck(gap and max(gap)<=wn+22,f"{tag} {ch}: bars start right next to the icon column (gap <= widest number + 22px)",[gap[:5],wn])
        ck(not er,f"{tag}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
