# t234: list-all list must never move on its own: scrollTop unchanged for 10s with simulated iOS toolbar height changes (<120px), re-render triggers and resize events; large resizes (keyboard/rotation) may relayout but a re-render never resets scroll
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
async def go(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile,device_scale_factor=2 if mobile else 1); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  n=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length"); ck(tag+" states list-all rows",n>=50,n)
  await pg.evaluate("()=>{const lv=document.getElementById('listView'); lv.scrollTop=420; document.getElementById('listView').querySelector('.lvgrid').dataset.mark='1'}"); await pg.wait_for_timeout(500)
  base_top=await pg.evaluate("()=>document.getElementById('listView').scrollTop"); ck(tag+" scrolled to a mid position",base_top>100,base_top)
  lo=vp['height']; hi=vp['height']+80; samples=[]
  for i in range(50):
    # toolbar collapse / expand (height only, <120px) + re-render triggers
    await pg.set_viewport_size({"width":vp['width'],"height":hi if i%2 else lo}); 
    if i%3==0: await pg.evaluate("()=>{ try{ window.__v2.renderList(); }catch(e){} }")
    if i%5==0: await pg.evaluate("()=>{ try{ window.__v2.refreshLayers(); }catch(e){} }")
    if i%7==0: await pg.evaluate("()=>{ window.dispatchEvent(new Event('resize')); }")
    await pg.wait_for_timeout(200)
    samples.append(await pg.evaluate("()=>{const lv=document.getElementById('listView'); const g=lv.querySelector('.lvgrid'); return [Math.round(lv.scrollTop), g&&g.dataset.mark==='1', Math.round(lv.getBoundingClientRect().top), window.scrollY]}"))
  tops={x[0] for x in samples}; ck(tag+" scrollTop never changed over 10s of toolbar changes/re-renders",tops=={base_top},sorted(tops)[:8])
  ck(tag+" list DOM was not rebuilt (same grid element every sample)",all(x[1] for x in samples),[x for x in samples if not x[1]][:3])
  ck(tag+" list top edge never moved",len({x[2] for x in samples})<=2,sorted({x[2] for x in samples}))
  ck(tag+" page never scrolled",all(x[3]==0 for x in samples),[x[3] for x in samples if x[3]][:3])
  # a real change (format) re-renders but keeps position
  await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
  t2=await pg.evaluate("()=>document.getElementById('listView').scrollTop"); ck(tag+" format change re-renders but keeps scroll position",abs(t2-base_top)<=2,(t2,base_top))
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await go(b,"phone",{"width":390,"height":664},True); await go(b,"desktop",{"width":1280,"height":700},False)
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
