# t229: one tap flips list sort direction at once; bubble names the new direction ~1.8s, no layout shift; alternates; persists
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
ORD="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>(r.querySelector('.nmx')||r).textContent.trim()).slice(0,12)"
BUB="()=>{const b=document.getElementById('laSortBub'); const r=b.getBoundingClientRect(); return {vis:!b.hidden&&r.width>0,txt:b.textContent,top:Math.round(r.top),right:Math.round(r.right)}}"
GEO="()=>{const lv=document.getElementById('listView'); const r=lv.querySelector('.lvrow.la').getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}"
async def run(b,tag,vp):
  pg=await b.new_page(viewport=vp); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
  o0=await pg.evaluate(ORD); g0=await pg.evaluate(GEO); ck(tag+" list-all US House AL rows",len(o0)>=7,o0)
  ck(tag+" no sort menu element visible",await pg.evaluate("()=>{const p=document.getElementById('laSortPop'); return !p||p.hidden}"))
  seq=[o0]; 
  for n in range(4):
    await pg.click("#laSort"); await pg.wait_for_timeout(250)
    o=await pg.evaluate(ORD); bb=await pg.evaluate(BUB); g=await pg.evaluate(GEO)
    ck(tag+" tap %d: order reversed vs previous"%(n+1),o==list(reversed(seq[-1])) or (o!=seq[-1] and set(o)==set(seq[-1])),(seq[-1],o))
    if n>=1: ck(tag+" tap %d: alternates (equals order %d taps ago)"%(n+1,2),o==seq[-2],(o,seq[-2]))
    exp="Low to high" if n%2==0 else "High to low"
    ck(tag+" tap %d: bubble '%s' shown"%(n+1,exp),bb['vis'] and bb['txt']==exp,bb)
    ck(tag+" tap %d: rows did not shift"%(n+1),g[0]==g0[0] and g[1]==g0[1] and g[3]==g0[3],(g,g0))
    seq.append(o)
  await pg.wait_for_timeout(1000); bb=await pg.evaluate(BUB); ck(tag+" bubble still up at ~1.3s",bb['vis'],bb)
  await pg.wait_for_timeout(1200); bb=await pg.evaluate(BUB); ck(tag+" bubble gone after ~2.2s",not bb['vis'],bb)
  sn=await pg.evaluate("()=>window.__stateSnapshot().so"); cur=await pg.evaluate("()=>window.__laInfo().sort")
  ck(tag+" direction persisted in snapshot",sn==cur,(sn,cur))
  ck(tag+" no page errors",not errs,errs[:3]); await pg.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"desktop",{"width":1280,"height":800}); await run(b,"phone",{"width":390,"height":780})
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
