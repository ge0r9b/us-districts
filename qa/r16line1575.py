import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from restore import chart
ST="()=>({thumbs:[...document.querySelectorAll('.cand')].filter(b=>b.offsetParent).map(b=>b.getAttribute('aria-label')),knobs:[...document.querySelectorAll('.kn')].filter(e=>e.offsetParent).map(e=>Math.round(e.getBoundingClientRect().left)),lbl:[...document.querySelectorAll('#barTime *')].filter(e=>e.childElementCount===0&&e.offsetParent&&e.textContent.trim()).map(e=>e.textContent.trim()).slice(0,6),chart:window.chartMode,ymode:window.__ymode&&window.__ymode(),rows:[...document.querySelectorAll('#listView .lvrow.la')].slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))})"
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3])
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for ck in sys.argv[4:]:
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(3000)
      kn=await pg.evaluate("()=>[...document.querySelectorAll('.kn')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})")
      trk=await pg.evaluate("()=>{const t=document.querySelector('.trk').getBoundingClientRect();return [t.left,t.right]}")
      left=min(kn,key=lambda k:k[0]); cdp=await c.new_cdp_session(pg)
      async def touch(t,x,y): await cdp.send('Input.dispatchTouchEvent',{'type':t,'touchPoints':[] if t=='touchEnd' else [{'x':x,'y':y}]})
      await touch('touchStart',*left)
      for i in range(1,11): await touch('touchMove',left[0]-(left[0]-trk[0])*i/10,left[1]); await pg.wait_for_timeout(30)
      await touch('touchEnd',0,0); await pg.wait_for_timeout(5000)
      pre=await pg.evaluate(ST); print(ck,'AFTERDRAG',json.dumps(pre)[:400],flush=True); await safeshot(pg,f"../shots/b1575-{eng[:2]}-{W}-r16-{ck}-afterdrag.png")
      await chart(pg,ck); await pg.wait_for_timeout(2000)
      a=await pg.evaluate(ST); await safeshot(pg,f"../shots/b1575-{eng[:2]}-{W}-r16-{ck}-before.png")
      await pg.wait_for_timeout(1500); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(10000)
      z=await pg.evaluate(ST); await safeshot(pg,f"../shots/b1575-{eng[:2]}-{W}-r16-{ck}-reload.png")
      print(ck,'BEFORE',json.dumps(a)[:500]); print(ck,'AFTER ',json.dumps(z)[:500]); print(' err',log['pageerr'][:2],log['console'][:2],flush=True); await c.close()
    await b.close()
asyncio.run(main())
