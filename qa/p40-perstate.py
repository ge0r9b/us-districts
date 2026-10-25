# QA-114: per-state district lists (All States > state) for a type; modes outer, states inner; 'no data' rows via DOM textContent
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="https://ge0r9b.github.io/us-districts/v2/"; ENG=sys.argv[1]; K=sys.argv[2]; LIM=int(sys.argv[3]) if len(sys.argv)>3 else 99
MODES=[("16","__ySetYr(0)"),("20","__ySetYr(1)"),("24","__ySetYr(2)"),("16-24","__ySet16(2)"),("20-24","__ySelectAll()")]
ROWS="()=>{const R=[...document.querySelectorAll('#listView .lvrow.la')];return {n:R.length,crumb:(document.getElementById('crumbs')||{}).textContent.trim(),nm:R.map(r=>(r.querySelector('.nmx')||r).textContent.trim()),nd:R.filter(r=>/no data/.test(r.textContent)).map(r=>(r.querySelector('.nmx')||r).textContent.trim().slice(0,50)),load:/Loading/.test(document.getElementById('listView').textContent)}}"
import os
if os.environ.get("MODES"): MODES=[m for m in MODES if m[0] in os.environ["MODES"].split(",")]
async def stable(pg,mn=2):
  prev=None
  for i in range(10):
    await pg.wait_for_timeout(900); r=await pg.evaluate(ROWS)
    if prev and not r['load'] and r['n']==prev['n'] and r['nd']==prev['nd'] and r['crumb']==prev['crumb'] and i>=mn: return r
    prev=r
  return r
async def main():
  out={}
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch(); c=await b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=(ENG=="chromium")); pg=await c.new_page()
    async def home():
      await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(6000)
      await pg.evaluate(f"()=>document.querySelector('#lyrRow .lbtn[data-k={K}]').click()"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>{const r=document.querySelector('li.la-row');(r.querySelector('.nmx')||r).click()}"); return await stable(pg)
    top=await home(); states=[s for s in top['nm']][:LIM]; print("states",len(states),top['crumb'],flush=True)
    for mnm,js in MODES:
      await pg.evaluate(f"()=>{{window.{js};return 0}}"); await pg.wait_for_timeout(3000)
      for st in states:
        ok=await pg.evaluate("n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n});if(!r)return false;r.querySelector('.nmx').click();return true}",st)
        if not ok:
          await home(); await pg.evaluate(f"()=>{{window.{js};return 0}}"); await pg.wait_for_timeout(3000)
          ok=await pg.evaluate("n=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n});if(!r)return false;r.querySelector('.nmx').click();return true}",st)
        r=await stable(pg,1); out[f"{K}|{mnm}|{st}"]={"ok":ok,"n":r['n'],"crumb":r['crumb'][:60],"nd":r['nd']}
        if r['nd'] or not ok: print(K,mnm,st,ok,r['n'],r['crumb'][:50],"ND",len(r['nd']),r['nd'][:30],flush=True)
        await pg.evaluate("()=>{window.__filterBack&&window.__filterBack();return 0}"); await stable(pg,1)
      print("mode done",K,mnm,"states with nd",sum(1 for kk,v in out.items() if kk.startswith(f"{K}|{mnm}|") and v['nd']),"rows nd",sum(len(v['nd']) for kk,v in out.items() if kk.startswith(f"{K}|{mnm}|")),flush=True)
    await b.close()
  json.dump(out,open(f"qa/p40-perstate-{ENG}-{K}.json","w"),indent=1)
asyncio.run(main())
