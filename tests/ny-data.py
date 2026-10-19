# QA-100/101: NY county rows are the official NYSBOE county results (incl. other candidates): Kings County and the NY state thumbnails in '16, '20, '24 (# mode), Chromium + WebKit 390.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500]),flush=True); (None if c else F.append(m))
ROW="""(n)=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent===n||r.querySelector('b.rn').title===n);if(!r)return null; return [...r.querySelectorAll('[data-party]')].map(e=>e.getAttribute('data-party')).join(' | ')}"""
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / ')"
EXP={0:('2016',['(Clinton): 640,553','(Trump): 141,044'],['4.56M','2.82M']),1:('2020',['(Biden): 703,310','(Trump): 202,772'],['5.24M','3.25M']),2:('2024',['(Harris): 601,265','(Trump): 233,964'],['4.62M','3.58M'])}
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=eng=='chromium',has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
      await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='NY').click()"); await pg.wait_for_timeout(7000)
      for i in (2,1,0):
        yr,kx,sx=EXP[i]
        await pg.evaluate("i=>{const w=document.getElementById('ysl'),t=w.querySelector('.tk[data-i=\"'+i+'\"]').getBoundingClientRect(),o={bubbles:true,clientX:t.left+t.width/2,clientY:t.top+t.height/2,pointerId:7,pointerType:'touch',isPrimary:true};w.dispatchEvent(new PointerEvent('pointerdown',o));w.dispatchEvent(new PointerEvent('pointerup',o))}",i); await pg.wait_for_timeout(6000)
        r=await pg.evaluate(ROW,'Kings County') or await pg.evaluate(ROW,'Kings')
        ck(r and all(x in r for x in kx),f"{eng} {yr}: Kings County = NYSBOE {kx}: {r}",r)
        th=await pg.evaluate(TH)
        ck(all(x in th for x in sx),f"{eng} {yr}: NY state thumbnails {sx}: {th}",th)
      ck(not er,f"{eng}: no page errors",er); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
