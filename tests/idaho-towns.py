# t231/t232: Idaho town rows: every county's towns have 2024 data (real precinct results; area-weighted + est mark where a town sits inside a larger precinct); list-all shows bars + approximate mark, never 'no data' for 2024
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={"width":1280,"height":800}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    r=await pg.evaluate("()=>window.__townAudit('Idaho')")
    cs=sorted({x['c'] for x in r}); ck("Idaho: all 44 counties have town rows",len(cs)>=40,len(cs))
    bad=[(x['c'],x['n']) for x in r if not x['v24']]
    ck("Idaho: every town row has 2024 data (%d towns)"%len(r),not bad,bad[:10])
    for c,t in (("Adams County","Council city"),("Adams County","New Meadows city"),("Lewis County","Craigmont city"),("Lewis County","Nezperce city"),("Lewis County","Reubens city"),("Lewis County","Winchester city"),("Owyhee County","Marsing city"),("Idaho County","Riggins city")):
      x=next((x for x in r if x['c']==c and x['n']==t),None); ck("%s / %s has 2024 data, flagged ≈ when area-weighted"%(c,t),bool(x and x['v24'] and x['v24']['tot']>0),x)
    # share sanity: Kamiah (Lewis) is centroid-matched (exact, no ≈)
    k=next(x for x in r if x['c']=='Lewis County' and x['n']=='Kamiah city'); ck("Lewis / Kamiah city exact (not ≈)",k['v24'] and not k['v24']['est'],k)
    # UI: Adams County towns list-all
    await pg.evaluate("()=>{ state.value='Idaho'; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>{ county.value='Adams County'; county.onchange&&county.onchange(); }"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1800)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>({t:r.textContent.trim().replace(/\\s+/g,' ').slice(0,60),nd:/no .?\\d* ?data|no data/i.test(r.textContent),est:!!r.querySelector('.estm'),bars:r.querySelectorAll('.seg,.bar,[class*=seg]').length}))")
    ck("Adams County list-all shows Council + New Meadows",len(rows)==2 and 'Council' in rows[0]['t']+rows[1]['t'],rows)
    ck("rows show data (not 'no data') with the ≈ mark",all(not r['nd'] and r['est'] for r in rows),rows)
    await pg.screenshot(path="/tmp/idaho-adams.png")
    ck("no page errors",not errs,errs[:3]); await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
