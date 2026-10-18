# usage: python3 tests/list-scroll-stay.py URL -- build 1563: a list keeps the scroll position the user leaves it at (PA counties, 2020, % mode,
# scrolled to the very bottom with touch / wheel), for 5 s of idle refreshes (label re-clamp, chart sync, update check); a drill-in still opens at the top.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:500]); fails+=0 if ok else 1
async def run(b,tag,vp):
  c=await b.new_context(viewport=vp,is_mobile=True,has_touch=True,device_scale_factor=2); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type("pennsylvania"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
  await pg.evaluate("()=>{const y=document.getElementById('yslider'); y.value=0; y.dispatchEvent(new Event('input',{bubbles:true})); window.__setNum('pct')}"); await pg.wait_for_timeout(3000)
  n=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length"); ck(f"{tag} PA counties list ({n} rows)",n>=60,n)
  cdp=await c.new_cdp_session(pg)
  for i in range(6): await cdp.send("Input.synthesizeScrollGesture",{"x":200,"y":int(vp["height"]*0.8),"yDistance":-1500,"speed":3000,"gestureSourceType":"touch"})
  await pg.mouse.move(200,500)
  for i in range(10): await pg.mouse.wheel(0,800); await pg.wait_for_timeout(60)
  await pg.wait_for_timeout(1200)
  S="()=>{const l=document.getElementById('listView'); return [l.scrollTop,l.scrollHeight-l.clientHeight]}"
  s0=await pg.evaluate(S); ck(f"{tag} scrolled to the very bottom ({s0})",s0[1]>200 and abs(s0[0]-s0[1])<=2,s0)
  last=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].pop(); return r.querySelector('.nmx').textContent}")
  tr=[]
  for i in range(10): await pg.wait_for_timeout(500); tr.append((await pg.evaluate(S))[0])
  ck(f"{tag} stays at the bottom for 5 s (last row {last})",all(abs(t-s0[0])<=2 for t in tr),tr)
  # mid-list position also kept
  await pg.evaluate("()=>{document.getElementById('listView').scrollTop=600}"); await pg.wait_for_timeout(300); m0=(await pg.evaluate(S))[0]; tr=[]
  for i in range(8): await pg.wait_for_timeout(500); tr.append((await pg.evaluate(S))[0])
  ck(f"{tag} a mid-list position is kept too",all(abs(t-m0)<=2 for t in tr),[m0,tr])
  # drill-in opens at the top
  await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent.startsWith('Susquehanna')).click()"); await pg.wait_for_timeout(7000)
  d=await pg.evaluate(S); ck(f"{tag} drill-in (Susquehanna townships) opens at the top",d[0]<=2,d)
  ck(f"{tag} no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'390',{'width':390,'height':844}); await run(b,'375',{'width':375,'height':667}); await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(m())
