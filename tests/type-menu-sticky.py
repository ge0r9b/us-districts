# usage: python3 tests/type-menu-sticky.py URL -- build 1564: the district-type menu (expands left from the right-column type button) stays open
# after a pick; another type switches the selection and the dark label moves with it. It closes only on (a) a tap outside (swallowed: the list
# row / map under it is not hit), (b) the main type button. Build 1565: tapping the selected type DESELECTS it (default view, label hidden,
# menu stays open); collapsed with nothing active, the main button shows the last used type's icon in the clear style; persisted across reloads. Real taps (phone) and clicks (iPad/desktop).
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:500]); fails+=0 if ok else 1
ST="""()=>({open:!document.getElementById('lyrRow').hidden,on:[...document.querySelectorAll('#lyrRow .lbtn.on')].filter(b=>b.style.display!=='none'&&b.dataset.k!=='counties').map(b=>b.dataset.k),lt:window.__dbg().lt,main:{typed:document.getElementById('bLyr').classList.contains('typed'),on:document.getElementById('bLyr').classList.contains('on'),k:document.getElementById('bLyr').dataset.lt,bg:getComputedStyle(document.getElementById('bLyr')).backgroundImage},
  lab:[...document.querySelectorAll('.tlab')].filter(x=>!x.hidden&&getComputedStyle(x).display!=='none'&&x.getBoundingClientRect().height>0).map(x=>{const r=x.getBoundingClientRect();return {t:x.textContent,cx:r.left+r.width/2,b:r.bottom}}),
  st:state.value,co:county.value,lm:document.body.classList.contains('listmode'),z:map.getZoom(),c:map.getCenter().lat.toFixed(4)})"""
BR="k=>{const b=document.querySelector(k);const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,r.top]}"
async def run(b,W,H,mob):
    errs=[]; c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=mob,has_touch=mob); pg=await c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    tap=(lambda x,y: pg.touchscreen.tap(x,y)) if mob else (lambda x,y: pg.mouse.click(x,y))
    async def tapsel(sel): x,y,_=await pg.evaluate(BR,sel); await tap(x,y); await pg.wait_for_timeout(1500)
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(6000)
    T=f"{W}px"
    await tapsel('#bLyr'); s=await pg.evaluate(ST); ck(f"{T}: main type button opens the menu",s['open'],s)
    await tapsel('#lyrRow .lbtn[data-k=ushouse]'); s=await pg.evaluate(ST)
    ck(f"{T}: picking US House keeps the menu open, US House selected, its dark label shown above it",s['open'] and s['on']==['ushouse'] and [x['t'] for x in s['lab']]==['US House'],s)
    x,y,top=await pg.evaluate(BR,'#lyrRow .lbtn[data-k=ushouse]'); ck(f"{T}: label centred above the selected button",s['lab'] and abs(s['lab'][0]['cx']-x)<=1.5 and s['lab'][0]['b']<=top,[s['lab'],x,top])
    await tapsel('#lyrRow .lbtn[data-k=senate]'); s=await pg.evaluate(ST)
    ck(f"{T}: another type (State senate) switches the selection, label moves, menu stays open",s['open'] and s['on']==['senate'] and len(s['lab'])==1 and 'senate' in s['lab'][0]['t'].lower(),s)
    x,y,top=await pg.evaluate(BR,'#lyrRow .lbtn[data-k=senate]'); ck(f"{T}: label now above State senate",s['lab'] and abs(s['lab'][0]['cx']-x)<=1.5,[s['lab'],x])
    # (c) build 1565: tap the selected type again -> deselected, default view, label hidden, menu stays open
    await tapsel('#lyrRow .lbtn[data-k=senate]'); s=await pg.evaluate(ST)
    ck(f"{T}: (c) tapping the selected type deselects it: no type selected, default view, no label, menu stays open",s['open'] and s['on']==[] and s['lt']=='counties' and not s['lab'],s)
    await tapsel('#lyrRow .lbtn[data-k=senate]'); s=await pg.evaluate(ST); ck(f"{T}: tapping it again re-selects it",s['open'] and s['on']==['senate'] and s['lt']=='senate',s)
    # (b) main button closes
    await tapsel('#bLyr'); s=await pg.evaluate(ST); ck(f"{T}: (b) the main type button closes it; a type is active -> main button dark with its icon",not s['open'] and s['on']==['senate'] and s['main']['typed'] and s['main']['k']=='senate' and '0, 0, 0, 0.88' in s['main']['bg'],s)
    await tapsel('#bLyr'); await tapsel('#lyrRow .lbtn[data-k=senate]'); s=await pg.evaluate(ST); ck(f"{T}: reopen + deselect",s['open'] and s['on']==[],s)
    await tapsel('#bLyr'); s=await pg.evaluate(ST); ck(f"{T}: collapsed with nothing active: main button shows the last used type (senate) in the clear style",not s['open'] and not s['main']['typed'] and not s['main']['on'] and s['main']['k']=='senate' and '255, 255, 255, 0.22' in s['main']['bg'],s)
    await pg.wait_for_timeout(1500); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(6000); s=await pg.evaluate(ST)
    ck(f"{T}: after a reload: still nothing selected, main button = last used (senate), clear",s['on']==[] and s['lt'] in ('counties','none') and not s['main']['typed'] and s['main']['k']=='senate',s)
    await tapsel('#bLyr'); await tapsel('#lyrRow .lbtn[data-k=senate]'); s=await pg.evaluate(ST); ck(f"{T}: re-select State senate after the reload",s['open'] and s['on']==['senate'],s)
    # (a) outside tap on a list row closes and is swallowed
    if not (await pg.evaluate(ST))['open']: await tapsel('#bLyr')
    s0=await pg.evaluate(ST)
    rx,ry,_=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>{const q=r.getBoundingClientRect();return q.top>200&&q.bottom<innerHeight-150})[0].querySelector('b.rn').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,0]}")
    await tap(rx,ry); await pg.wait_for_timeout(2500); s=await pg.evaluate(ST)
    ck(f"{T}: (a) a tap on a list row outside the menu closes it",s0['open'] and not s['open'] and s['on']==['senate'],[s0,s])
    ck(f"{T}: (a) ...and is swallowed: the row was not opened (still the same list/state/zoom)",s['st']==s0['st'] and s['co']==s0['co'] and s['z']==s0['z'] and s['c']==s0['c'],[s0,s])
    await tap(rx,ry); await pg.wait_for_timeout(4000); s=await pg.evaluate(ST); ck(f"{T}: with the menu closed, the same tap reaches the row again (it opens: {s['co'] or s['z']})",not s['open'] and (s['co']!=s0['co'] or s['z']!=s0['z'] or s['c']!=s0['c']),[s0,s])
    ck(f"{T}: no page errors",not errs,errs); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,390,844,True); await run(b,1024,768,False); await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
