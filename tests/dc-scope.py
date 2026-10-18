# QA-072: DC (geo field + Enter) keeps DC as the scope for School districts / US House / State senate: DC numbers, DC rows only
import asyncio,sys,re
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "http://localhost:8844/v2/"
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
BAD="()=>[...document.querySelectorAll('#cands .cand .cpt, #laCands .lact .cpt')].filter(e=>e.getBoundingClientRect().width>0).map(e=>e.textContent)"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>(r.querySelector('.nmx')||r).textContent.trim())"
async def geo(pg,q):
  await pg.evaluate("()=>{ const b=document.querySelector('#barGeo .fsq input')||document.getElementById('gq'); b.focus(); b.click(); }"); await pg.wait_for_timeout(600)
  await pg.keyboard.type(q); await pg.wait_for_timeout(800); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
async def typ(pg,k):
  if not await pg.evaluate(f"()=>{{const e=document.querySelector('#lyrRow .lbtn[data-k={k}]'); return !!(e&&e.getBoundingClientRect().width)}}"):
    await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
  await pg.evaluate(f"()=>{{const e=document.querySelector('#lyrRow .lbtn[data-k={k}]'); if(!e.classList.contains('on')) e.click()}}"); await pg.wait_for_timeout(3500)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in [(390,844),(1024,768)]:
      pg=await b.new_page(viewport={'width':W,'height':H},is_mobile=W<800,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await geo(pg,"District of Columbia")
      t0=await pg.evaluate(BAD); ck(len(t0)==2 and t0[0] in ("90%","92%"),f"{W} DC: thumbnails {t0}")
      for k in ["schools","ushouse","senate"]:
        await typ(pg,k)
        t=await pg.evaluate(BAD); ck(t==t0,f"{W} DC > {k} map: thumbnails {t} (DC {t0})")
        if await pg.evaluate("()=>!document.body.classList.contains('listmode')"): await pg.evaluate("()=>document.getElementById('bGlobe').click()")
        await pg.wait_for_timeout(3500)
        r=await pg.evaluate(ROWS); ttl=await pg.evaluate("()=>[...document.querySelectorAll('#crumbs .crumb')].map(c=>c.textContent.trim()).join('>')")
        ck(1<=len(r)<=12 and not any(re.fullmatch(r'[A-Z]{2}(-\d+)?',x) for x in r),f"{W} DC > {k} list: {len(r)} rows {r[:4]} title '{ttl}'")
        t=await pg.evaluate(BAD); ck(not t or t==t0 or all('%' in x for x in t),f"{W} DC > {k} list thumbnails {t}")
        await pg.evaluate("()=>{ if(document.body.classList.contains('listmode')) document.getElementById('bGlobe').click() }"); await pg.wait_for_timeout(2500)
      await geo(pg,"Delaware")
      t=await pg.evaluate(BAD); ck(t and t!=t0,f"{W} Delaware after DC: thumbnails {t} (not DC)")
      ck(not er,f"{W}: no page errors {er[:2]}")
      await pg.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
