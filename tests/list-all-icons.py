# usage: python3 tests/list-all-icons.py URL tag -- every list-all row has its icon centered on x=27 and its name at x=52 (x=73 / 98 when the left candidate column is shown, build 1546; single-year result/chart rows since 1551: no row icon, name at x=52 = the top fields' text) (countries, states, provinces, counties, townships, precincts, districts)
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
MEAS="""()=>{const rows=[...document.querySelectorAll('#listView .lvrow.la')]; const vis=rows.filter(r=>r.getBoundingClientRect().height>0); const L=document.getElementById("listView").getBoundingClientRect(); const out=vis.filter(r=>{const q=r.getBoundingClientRect();return q.bottom>L.top&&q.top<L.bottom}).slice(0,60).map(r=>{const o=r.querySelector('.oic'),n=r.querySelector('b.rn'); const ob=o.getBoundingClientRect(); const img=o.querySelector('img'); const sv=o.querySelector('svg'); const rg=document.createRange(); rg.selectNodeContents(n.querySelector(".nmx")||n.lastChild||n); /* build 1564: the name, not the hidden .estm marker of estimated rows */ const nb=rg.getBoundingClientRect(); const cmp=r.classList.contains('cmp')&&!r.closest('.lvgrid.dl'); return {cmp,ohid:getComputedStyle(o).display==='none',c:Math.round(ob.left+ob.width/2),t:Math.round(nb.left),has:!!(img?(img.complete&&img.naturalWidth>0):(sv&&sv.querySelector('path')))}});
 return {n:rows.length,vis:vis.length,onscreen:vis.length>0&&vis[0].getBoundingClientRect().left>=0&&vis[0].getBoundingClientRect().right<=innerWidth+1,bad:out.filter(x=>x.cmp?(!x.ohid||x.t!==52):(x.c!==27+(document.body.classList.contains('lathumb')?46:0)||x.t!==52+(document.body.classList.contains('lathumb')?46:0)||!x.has)).slice(0,4),title:window.__LA.title,first:vis[0]&&vis[0].innerText.replace(/\\n/g,' | ').slice(0,70)}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((430,900,'ph'),(1280,800,'dk')):
      async def fresh():
        pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500); return pg
      async def opn(pg):
        await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1800)
      async def clk(pg,sel,tx):
        r=await pg.evaluate("([s,t])=>{const l=[...document.querySelectorAll(s)].find(l=>l.innerText.trim().includes(t)); if(l){l.click(); return true} return false}",[sel,tx]); await pg.wait_for_timeout(3000); return r
      async def go(pg,name,min_rows):
        global fails
        await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); l&&l.click()}"); await pg.wait_for_timeout(6000)
        m=await pg.evaluate(MEAS); ok=m['vis']>=min_rows and not m['bad'] and m['onscreen']; fails+=0 if ok else 1
        print('OK  ' if ok else 'FAIL',t,name,json.dumps(m)[:300],flush=True); await pg.screenshot(path=f"/workspace/shots/lai-{tag}-{t}-{name}.png")
      # countries
      pg=await fresh(); await pg.evaluate("()=>window.__allPick()"); await pg.wait_for_timeout(1500); await opn(pg); await go(pg,'countries',100); await pg.close()
      # states
      pg=await fresh(); await opn(pg); await go(pg,'states',51); await pg.close()
      # provinces
      pg=await fresh(); await pg.evaluate("()=>window.__worldEnter('ca')"); await pg.wait_for_timeout(2500); await opn(pg); await go(pg,'provinces',13); await pg.close()
      # counties + townships
      pg=await fresh(); await opn(pg); await clk(pg,'.foldlist li','Pennsylvania'); await opn(pg); await go(pg,'counties',60)
      await pg.evaluate("()=>window.__laExit()"); await opn(pg); await clk(pg,'.foldlist li:not(.la-row)','Allegheny County'); await opn(pg); await go(pg,'townships',100); await pg.close()
      # districts
      for key,lab in (('ushouse','US House districts'),('senate','State senate districts'),('statehouse','State house districts'),('schools','School districts')):
        pg=await fresh(); await opn(pg); await clk(pg,'#orgTypes li',lab); await opn(pg); await clk(pg,'.foldlist li','Pennsylvania'); await opn(pg); await go(pg,'districts-'+key,10)
        if key=='ushouse':
          await pg.evaluate("()=>window.__laExit()"); await opn(pg)
          await pg.locator('#sheet .foldlist li',has_text='District 03').first.locator('.go').click(); await pg.wait_for_timeout(5000); await opn(pg); await go(pg,'precincts',100)
        await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
