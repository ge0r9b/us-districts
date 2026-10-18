# usage: python3 tests/type-labels.py URL -- district-type buttons (US House, State senate, State house, School districts) carry
# their names. Since build 1553 (new app, users learning) the labels are persistent white chips sitting 3-4px above their
# button (no overlap, build 1554; 1553 overlapped 3px), never auto-hiding: the type button (bLyr) always shows the current type's name; with the type row open every
# type button shows its own; long-press never picks a type; labels take no taps and never collide; list view too.
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
EXP={"ushouse":"US House","senate":"State senate","statehouse":"State house","schools":"School districts"}
LABS="""()=>[...document.querySelectorAll('.tlab')].filter(x=>!x.hidden&&getComputedStyle(x).display!=='none').map(e=>{const r=e.getBoundingClientRect(); const s=getComputedStyle(e); return {t:e.textContent,k:e.dataset.k,l:r.left,r:r.right,top:r.top,b:r.bottom,bg:s.backgroundColor,col:s.color,pe:s.pointerEvents}})"""
RECT="k=>{const r=document.querySelector(k.startsWith('#')?k:'#lyrRow .lbtn[data-k='+k+']').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,top:r.top,l:r.left,r:r.right}}"
def tucked(lb,r): return lb and r['top']-5<=lb['b']<=r['top']-2.5 and lb['l']<r['x']<lb['r']  # 3-4px gap above the button, no overlap (build 1554)
async def openRow(pg):
  if await pg.evaluate("()=>document.getElementById('lyrRow').hidden"): await pg.tap("#bLyr"); await pg.wait_for_timeout(700)
async def closeRow(pg):
  if not await pg.evaluate("()=>document.getElementById('lyrRow').hidden"): await pg.tap("#bLyr"); await pg.wait_for_timeout(700)
async def phone(b):
  c=await b.new_context(viewport={"width":430,"height":932},has_touch=True,is_mobile=True,device_scale_factor=2)
  pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  L=await pg.evaluate(LABS); h=await pg.evaluate(RECT,'#bLyr')
  ck("phone, row closed: the type button carries a label (US House by default), 3-4px above it, no overlap",len(L)==1 and L[0]['t']=='US House' and tucked(L[0],h),[L,h])
  ck("phone: labels are white with dark text and take no taps",L and L[0]['bg']=='rgb(255, 255, 255)' and L[0]['col']=='rgb(28, 28, 30)' and L[0]['pe']=='none',L)
  await openRow(pg)
  al=await pg.evaluate("()=>Object.fromEntries([...document.querySelectorAll('#lyrRow .lbtn')].map(b=>[b.dataset.k,b.getAttribute('aria-label')]))")
  for k,v in EXP.items(): ck("phone %s button aria-label '%s'"%(k,v),al.get(k)==v,al)
  L=await pg.evaluate(LABS); by={x['t']:x for x in L}
  for k,v in EXP.items():
    r=await pg.evaluate(RECT,k); ck("phone, row open: '%s' label 3-4px above its button"%v,tucked(by.get(v),r),[by.get(v),r])
  srt=sorted(L,key=lambda x:x['l']); ck("phone, row open: labels never overlap each other",all(a['r']<=b2['l']+0.5 for a,b2 in zip(srt,srt[1:])),srt)
  hit=await pg.evaluate("""()=>{const L=[...document.querySelectorAll('.tlab')].filter(x=>!x.hidden).map(e=>e.getBoundingClientRect()); const B=[...document.querySelectorAll('#lyrRow .lbtn,.rbtn')].map(e=>e.getBoundingClientRect()).filter(r=>r.width>0); return L.flatMap(l=>B.filter(b=>b.left<l.right&&b.right>l.left&&b.top<l.bottom&&b.bottom>l.top).map(b=>[l.left,l.top,b.left,b.top]))}""")
  ck("phone, row open: no label overlaps any button",not hit,hit)
  await pg.screenshot(path="/workspace/shots/type-labels-open.png")
  cdp=await c.new_cdp_session(pg); r=await pg.evaluate(RECT,'senate')
  await cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":r['x'],"y":r['y']}]}); await pg.wait_for_timeout(200)
  await cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":r['x']+3,"y":r['y']+2}]}); await pg.wait_for_timeout(500)
  await cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]}); await pg.wait_for_timeout(300)
  ck("phone long-press senate does not pick the type (row still open)",not await pg.evaluate("()=>document.getElementById('lyrRow').hidden"))
  for k,v in EXP.items():
    await openRow(pg)
    if await pg.evaluate("k=>!!document.querySelector('#lyrRow .lbtn.on[data-k='+k+']')",k): await pg.tap("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(1500); await openRow(pg)
    await pg.tap("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(2600)
    await closeRow(pg); L=await pg.evaluate(LABS); h=await pg.evaluate(RECT,'#bLyr')
    ck("phone tap %s: type button label '%s', still shown after 2.6s"%(k,v),len(L)==1 and L[0]['t']==v and tucked(L[0],h),[L,h])
  # list view: the label stays, clear of the row names
  await pg.evaluate("()=>window.__v2.setView('list')"); await pg.wait_for_timeout(4000)
  L=await pg.evaluate(LABS); nm=await pg.evaluate("()=>Math.max(0,...[...document.querySelectorAll('#listView .lvrow .nmx')].filter(e=>e.offsetParent).map(e=>{const g=document.createRange(); g.selectNodeContents(e); return g.getBoundingClientRect().right}))")
  ck("phone list view: type label shown, right of every row name",len(L)==1 and L[0]['l']>nm,[L,nm])
  await pg.screenshot(path="/workspace/shots/type-labels-list.png")
  ck("phone no page errors",not errs,errs[:3]); await c.close()
async def desk(b):
  c=await b.new_context(viewport={"width":1280,"height":800}); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.click("#bLyr"); await pg.wait_for_timeout(700)
  L={x['t'] for x in await pg.evaluate(LABS)}
  ck("desktop row open: every type button labelled",all(v in L for v in EXP.values()),L)
  ck("desktop no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await phone(b); await desk(b); await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
