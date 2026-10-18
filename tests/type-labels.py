# usage: python3 tests/type-labels.py URL -- t266: district-type buttons (US House, State senate, State house, School districts) carry their label
# bubbles again: every button has an aria-label; long-press shows its name above the button without picking it (even with
# finger jitter), a tap shows the picked type's name above the type button; desktop hover shows it too
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
EXP={"ushouse":"US House","senate":"State senate","statehouse":"State house","schools":"School districts"}
BUB="""()=>{const e=[...document.querySelectorAll('.bub')].find(x=>!x.hidden&&getComputedStyle(x).display!=='none'); if(!e) return null; const r=e.getBoundingClientRect(); return {t:e.textContent,x:r.left,y:r.top,w:r.width,h:r.height,b:r.bottom}}"""
RECT="k=>{const r=document.querySelector('#lyrRow .lbtn[data-k='+k+']').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,top:r.top,l:r.left,r:r.right}}"
async def openRow(pg):
  if await pg.evaluate("()=>document.getElementById('lyrRow').hidden"): await pg.tap("#bLyr"); await pg.wait_for_timeout(700)
async def phone(b):
  c=await b.new_context(viewport={"width":430,"height":932},has_touch=True,is_mobile=True,device_scale_factor=2)
  pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await openRow(pg)
  al=await pg.evaluate("()=>Object.fromEntries([...document.querySelectorAll('#lyrRow .lbtn')].map(b=>[b.dataset.k,b.getAttribute('aria-label')]))")
  for k,v in EXP.items(): ck("phone %s button aria-label '%s'"%(k,v),al.get(k)==v,al)
  cdp=await c.new_cdp_session(pg)
  for k,v in EXP.items():
    await openRow(pg); lt0=await pg.evaluate("()=>window.__v2&&window.__v2.ltype!==undefined?window.__v2.ltype:(document.querySelector('#lyrRow .lbtn.on')||{dataset:{}}).dataset.k")
    r=await pg.evaluate(RECT,k)
    await cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":r['x'],"y":r['y']}]})
    await pg.wait_for_timeout(200); await cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":r['x']+3,"y":r['y']+2}]})
    await pg.wait_for_timeout(500); bb=await pg.evaluate(BUB)
    if k=="senate": await pg.screenshot(path="/workspace/shots/type-labels-longpress-senate.png")
    ck("phone long-press %s (with 3px jitter): bubble '%s' above the button"%(k,v),bb and bb['t']==v and bb['b']<=r['top'] and bb['x']<r['r'] and bb['x']+bb['w']>r['l'],{'bub':bb,'btn':r})
    await cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]}); await pg.wait_for_timeout(300)
    ck("phone long-press %s does not pick the type (row still open)"%k,not await pg.evaluate("()=>document.getElementById('lyrRow').hidden"))
    await pg.wait_for_timeout(2200)
  for k,v in EXP.items():
    await openRow(pg)
    if await pg.evaluate("k=>!!document.querySelector('#lyrRow .lbtn.on[data-k='+k+']')",k): await pg.tap("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(1500); await openRow(pg)
    await pg.tap("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(250); bb=await pg.evaluate(BUB)
    h=await pg.evaluate("()=>{const r=document.getElementById('bLyr').getBoundingClientRect();return {top:r.top,l:r.left,r:r.right}}")
    if k=="schools": await pg.screenshot(path="/workspace/shots/type-labels-tap-schools.png")
    ck("phone tap %s: bubble '%s' above the type button"%(k,v),bb and bb['t']==v and bb['b']<=h['top'] and bb['x']<h['r'],{'bub':bb,'host':h})
    await pg.wait_for_timeout(1700); bb=await pg.evaluate(BUB); ck("phone tap %s: bubble gone after ~2s"%k,not bb,bb)
  ck("phone no page errors",not errs,errs[:3]); await c.close()
async def desk(b):
  c=await b.new_context(viewport={"width":1280,"height":800}); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.click("#bLyr"); await pg.wait_for_timeout(700)
  for k,v in EXP.items():
    await pg.hover("#lyrRow .lbtn[data-k=%s]"%k); await pg.wait_for_timeout(300); bb=await pg.evaluate(BUB)
    ck("desktop hover %s: bubble '%s'"%(k,v),bb and bb['t']==v,bb)
  ck("desktop no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await phone(b); await desk(b); await b.close()
  print("FAILS",fails)
asyncio.run(main())
