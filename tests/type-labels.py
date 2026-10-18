# usage: python3 tests/type-labels.py URL -- build 1563: ONE dark label (rgba(0,0,0,.8), white text) centred 4px above the SELECTED type button, only while the row is open.
# Earlier: district-type buttons (US House, State senate, State house, School districts) carry
# their names (white chips 3-4px above their button, never colliding; long-press never picks a type; labels take no taps).
# Build 1560 (supersedes 'always persistent', 1553): labels show ONLY while the type row is expanded (every button labelled); the
# collapsed type button shows none. Labels are single-line (10px, nowrap); in the open row 'School districts' reads 'Schools'; runs at 430 and 390px; overlapping neighbours are spread around their buttons' mean centre so each still spans its button's centre.
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
EXP={"ushouse":"US House","senate":"State senate","statehouse":"State house","schools":"School districts"}
LABS="""()=>[...document.querySelectorAll('.tlab')].filter(x=>!x.hidden&&getComputedStyle(x).display!=='none').map(e=>{const r=e.getBoundingClientRect(); const s=getComputedStyle(e); const g=document.createRange(); g.selectNodeContents(e); return {t:e.textContent,k:e.dataset.k,l:r.left,r:r.right,top:r.top,b:r.bottom,bg:s.backgroundColor,col:s.color,pe:s.pointerEvents,lines:g.getClientRects().length,fs:parseFloat(s.fontSize)}})"""
OPEN=dict(EXP,schools="Schools")
RECT="k=>{const r=document.querySelector(k.startsWith('#')?k:'#lyrRow .lbtn[data-k='+k+']').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,top:r.top,l:r.left,r:r.right}}"
def tucked(lb,r): return lb and r['top']-5<=lb['b']<=r['top']-2.5 and lb['l']<r['x']<lb['r']  # 3-4px gap above the button, no overlap (build 1554)
async def openRow(pg):
  if await pg.evaluate("()=>document.getElementById('lyrRow').hidden"): await pg.tap("#bLyr"); await pg.wait_for_timeout(700)
async def closeRow(pg):
  if not await pg.evaluate("()=>document.getElementById('lyrRow').hidden"): await pg.tap("#bLyr"); await pg.wait_for_timeout(700)
async def phone(b,W=430,H=932):
  c=await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=True,device_scale_factor=2)
  pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  L=await pg.evaluate(LABS)
  ck("phone %d, row closed: the type button shows NO label (build 1560)"%W,len(L)==0,L)
  await openRow(pg)
  al=await pg.evaluate("()=>Object.fromEntries([...document.querySelectorAll('#lyrRow .lbtn')].map(b=>[b.dataset.k,b.getAttribute('aria-label')]))")
  for k,v in EXP.items(): ck("phone %s button aria-label '%s'"%(k,v),al.get(k)==v,al)
  L=await pg.evaluate(LABS); sel=await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn.on'); return b?b.dataset.k:null}")
  ck("phone %d, row open: at most ONE label, only for the selected type (build 1563) (%s)"%(W,sel),len(L)==(1 if sel else 0) and (not sel or L[0]['k']==sel),L)
  cdp=await c.new_cdp_session(pg); r=await pg.evaluate(RECT,'senate')
  await cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":r['x'],"y":r['y']}]}); await pg.wait_for_timeout(200)
  await cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":r['x']+3,"y":r['y']+2}]}); await pg.wait_for_timeout(500)
  await cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]}); await pg.wait_for_timeout(300)
  ck("phone long-press senate does not pick the type (row still open)",not await pg.evaluate("()=>document.getElementById('lyrRow').hidden"))
  for k,v in EXP.items():
    await openRow(pg)
    if await pg.evaluate("k=>!!document.querySelector('#lyrRow .lbtn.on[data-k='+k+']')",k): await pg.tap("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(1500); await openRow(pg)
    await pg.tap("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(2600)
    on=await pg.evaluate("k=>!!document.querySelector('#lyrRow .lbtn.on[data-k='+k+']')",k)
    await closeRow(pg); L=await pg.evaluate(LABS)
    ck("phone tap %s: type picked, row collapsed -> no label (build 1560)"%k,on and len(L)==0,[on,L])
    await openRow(pg); L=await pg.evaluate(LABS); r=await pg.evaluate(RECT,k)
    ck("phone %d, %s selected + row open: exactly one label '%s'"%(W,k,EXP[k]),len(L)==1 and L[0]['t']==EXP[k] and L[0]['k']==k,L)
    lb=L[0] if L else None
    ck("phone %d, %s label: dark smoky fill, white text, single line 10px, takes no taps"%(W,k),lb and lb['bg']=='rgba(0, 0, 0, 0.8)' and lb['col']=='rgb(255, 255, 255)' and lb['lines']==1 and lb['fs']==10 and lb['pe']=='none',lb)
    ck("phone %d, %s label centred above its button, ~4px gap"%(W,k),lb and abs((lb['l']+lb['r'])/2-r['x'])<=1 and 3<=r['top']-lb['b']<=5 and lb['l']>=0 and lb['r']<=W,[lb,r])
    if k=='ushouse' and W==390: await pg.screenshot(path="/workspace/glass-built-typelabel-local.png")
    await closeRow(pg)
  # list view: collapsed -> no label; expanded -> every button labelled, one line
  await pg.evaluate("()=>window.__v2.setView('list')"); await pg.wait_for_timeout(4000)
  L=await pg.evaluate(LABS); ck("phone list view, row collapsed: no label",len(L)==0,L)
  await openRow(pg); L=await pg.evaluate(LABS)
  ck("phone list view, row open: one single-line label (the selected type)",len(L)==1 and all(x['lines']==1 for x in L),L)
  await pg.screenshot(path="/workspace/shots/type-labels-list-%d.png"%W); await closeRow(pg)
  ck("phone no page errors",not errs,errs[:3]); await c.close()
async def desk(b):
  c=await b.new_context(viewport={"width":1280,"height":800}); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  L0=await pg.evaluate(LABS); ck("desktop row collapsed: no label",len(L0)==0,L0)
  await pg.click("#bLyr"); await pg.wait_for_timeout(700)
  L=await pg.evaluate(LABS); sel=await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn.on'); return b?b.dataset.k:null}")
  ck("desktop row open: one label for the selected type only (build 1563)",len(L)==(1 if sel else 0),[sel,L])
  ck("desktop no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await phone(b); await phone(b,390,844); await desk(b); await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
