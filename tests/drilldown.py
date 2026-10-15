# usage: python3 tests/drilldown.py URL tag -- list-all drill-down chain in the SAME list view + settings: All States -> Florida (counties) -> Pasco County (towns) -> a town (precincts); no map switch, settings persist, field labels follow; desktop + phone
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
S="()=>({la:window.__LA.on,lv:window.__LA.lv&&window.__LA.lv.id,n:document.querySelectorAll('#listView .lvrow.la').length,list:document.body.classList.contains('listmode'),st:state.value,co:county.value,snap:window.__stateSnapshot(),field:(document.querySelector('#crumbs .crumb.cur')||{}).textContent,head:(document.querySelector('#listView .lvhead')||{}).textContent,seg:document.querySelectorAll('#listView .lvrow.la .sg b').length})"
def chk(n,ok,i=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,json.dumps(i)[:420],flush=True)
async def tapRow(pg,pred):
  ok=await pg.evaluate("p=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(x=>x.offsetParent&&eval(p)); if(!r) return false; r.querySelector('b.rn').click(); return true}",pred); return ok
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t,touch in((1280,800,'dk',False),(430,800,'ph',True)):
      ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=touch,is_mobile=touch,user_agent=UA if touch else None); pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)[:100]))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.click("#bGeo"); await pg.wait_for_timeout(900); await pg.click("li.la-row"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(800)
      ok=await tapRow(pg,"x.querySelector('b.rn').title==='Florida'"); await pg.wait_for_timeout(7000); s=await pg.evaluate(S)
      chk(f'{t} FL row -> counties list (67 rows, same list view, values inside bars)',ok and s['lv']=='counties' and s['n']==67 and s['list'] and s['seg']>50,s); await pg.screenshot(path=f"/workspace/shots/dd-{tag}-{t}-1counties.png")
      ok=await tapRow(pg,"x.querySelector('b.rn').title==='Pasco County'"); await pg.wait_for_timeout(7000); s=await pg.evaluate(S)
      chk(f'{t} Pasco row -> towns list',ok and s['lv']=='townships' and s['n']>=3 and s['list'] and s['co']=='Pasco County',s); await pg.screenshot(path=f"/workspace/shots/dd-{tag}-{t}-2towns.png")
      ok=await tapRow(pg,"true"); await pg.wait_for_timeout(7000); s=await pg.evaluate(S)
      chk(f'{t} town row -> precincts list (same list view)',ok and s['lv']=='precincts' and s['n']>=1 and s['list'],s); await pg.screenshot(path=f"/workspace/shots/dd-{tag}-{t}-3precincts.png")
      chk(f'{t} no page errors',not errs,errs); await ctx.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
