# usage: python3 tests/list-all-values.py URL tag -- list-all bars: value written INSIDE each segment (% in % mode, votes in # mode, change in delta mode), hidden when the segment is too narrow, bubbles still give exact values; list rows do not shift over 8s idle (no jumping); desktop + phone
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
def chk(n,ok,i=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,json.dumps(i)[:330],flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bGeo"); await pg.wait_for_timeout(900); await pg.click("li.la-row"); await pg.wait_for_timeout(4000)
      Q="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent).slice(0,10).map(r=>[...r.querySelectorAll('.sg')].map(s=>s.innerText.trim()))"
      for mode in ('pct','num'):
        await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1800); r=await pg.evaluate(Q); txt=[x for row in r for x in row if x]
        ok=len(txt)>=12 and all(('%' in x) if mode=='pct' else (not '%' in x and re.match(r'^[\d.,]+[MK]?$',x)) for x in txt) and all(len(row)==3 for row in r)
        chk(f'{t} {mode}: values inside bar segments',ok,r[:3]); await pg.screenshot(path=f"/workspace/shots/lv-{tag}-{t}-{mode}.png")
      await pg.click("#bTime"); await pg.wait_for_timeout(500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000)
      r=await pg.evaluate(Q); txt=[x for row in r for x in row if x]; chk(f'{t} delta: change values inside segments',len(txt)>=(6 if t=='dk' else 1) and all(re.match(r'^[+\u2212]',x) for x in txt),r[:3]); await pg.screenshot(path=f"/workspace/shots/lv-{tag}-{t}-delta.png")
      await pg.evaluate("()=>{ window.__s=[]; const lv=document.getElementById('listView'); setInterval(()=>{ const r=lv.getBoundingClientRect(),w=lv.querySelector('.lvrow.la'); window.__s.push([Math.round(r.top),Math.round(r.height),lv.scrollTop,w?Math.round(w.getBoundingClientRect().top):0]); },100); }"); await pg.wait_for_timeout(8000)
      u=await pg.evaluate("()=>[...new Set(window.__s.map(x=>x.join(',')))]"); chk(f'{t} list stable over 8s idle (no jumping)',len(u)==1,u)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
