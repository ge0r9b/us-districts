# pass 31 (build 1610): QA-074 fix check: same-name school districts labelled with county; is the label visible in the row?
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for stn in sys.argv[3].split(','):
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      await pg.evaluate("n=>{const s=document.getElementById('state');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}))}",stn); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
      await pg.touchscreen.tap(*(await center(pg,'#lyrRow .lbtn[data-k=schools]'))); await pg.wait_for_timeout(5000)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(7000)
      rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>{const n=r.querySelector('.nmx')||r;const cs=getComputedStyle(n);return {t:n.textContent.trim(),title:r.getAttribute('title')||n.getAttribute('title')||'',aria:r.getAttribute('aria-label')||'',sw:n.scrollWidth,cw:n.clientWidth,to:cs.textOverflow}})")
      vis=[r['t'] for r in rows]; full=[r['title'] or r['aria'] or r['t'] for r in rows]
      paren=[r for r in rows if '(' in r['t'] or '(' in r['title'] or '(' in r['aria']]
      o=out[stn]={'n':len(rows),'dup_visible':sorted({v for v in vis if vis.count(v)>1}),'n_dup_visible_rows':sum(1 for v in vis if vis.count(v)>1),'dup_full':sorted({v for v in full if full.count(v)>1}),'paren_rows':paren[:12],'n_paren':len(paren)}
      for i,r in enumerate(rows):
        if r['t'].startswith('Eastern Local') or r['t'].startswith('Eureka City'):
          o.setdefault('examples',[]).append(r)
      # scroll a labelled row into view and screenshot
      tgt=(paren[0]['t'] if paren else None)
      if tgt:
        await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow.la .nmx')].find(e=>e.textContent.trim()===t);e&&e.scrollIntoView({block:'center'})}",tgt); await pg.wait_for_timeout(800)
      await safeshot(pg,f"shotsh1600/b1618h-{eng[:2]}-{W}x{H}-074-{stn.replace(' ','')}.png")
      print(stn,json.dumps(o)[:2500],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h1600-074-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
