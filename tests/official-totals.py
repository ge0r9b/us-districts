# QA-003 (user rule): state rows, state thumbnails and the national numbers are the official certified totals (FEC; NY = NYSBOE incl. fusion) in '16, '20, '24.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500]),flush=True); (None if c else F.append(m))
ROW="""(n)=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent===n);if(!r)return null; return [...r.querySelectorAll('[data-party]')].map(e=>e.getAttribute('data-party')).join(' | ')}"""
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / ')"
TAP="i=>{const w=document.getElementById('ysl'),t=w.querySelector('.tk[data-i=\"'+i+'\"]').getBoundingClientRect(),o={bubbles:true,clientX:t.left+t.width/2,clientY:t.top+t.height/2,pointerId:7,pointerType:'touch',isPrimary:true};w.dispatchEvent(new PointerEvent('pointerdown',o));w.dispatchEvent(new PointerEvent('pointerup',o))}"
EXP={2:[('PA','(Harris): 3,423,042','(Trump): 3,543,308'),('NY','(Harris): 4,619,543','(Trump): 3,579,519'),('GA','(Harris): 2,548,017',None)],
     1:[('PA','(Biden): 3,458,229','(Trump): 3,377,674'),('NY','(Biden): 5,244,886','(Trump): 3,251,997'),('AZ','(Biden): 1,672,143',None)],
     0:[('PA','(Clinton): 2,926,441','(Trump): 2,970,733'),('MI','(Clinton): 2,268,839','(Trump): 2,279,543')]}
EXACT={"2": {"US": [75019578, 77304188, 155241934], "New York": [4619543, 3579519, 8263474], "Pennsylvania": [3423042, 3543308, 7058732], "Maine": [435652, 377977, 831375], "Wyoming": [69527, 192633, 269048], "Virginia": [2335395, 2075085, 4505941]}, "1": {"US": [81283501, 74223975, 158429631], "New York": [5244886, 3251997, 8616861], "Pennsylvania": [3458229, 3377674, 6936976], "Maine": [435072, 360737, 819461], "Wyoming": [73491, 193559, 276765], "Virginia": [2413568, 1962430, 4460524]}, "0": {"US": [65853514, 62984828, 136669276], "New York": [4556118, 2819533, 7721442], "Pennsylvania": [2926441, 2970733, 6165478], "Maine": [357735, 335593, 747927], "Wyoming": [55973, 174419, 255849], "Virginia": [1981473, 1769443, 3984631]}}
NAT0={2:('75.0M','77.3M'),1:('81.3M','74.2M'),0:('65.9M','63.0M')}
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=eng=='chromium',has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
      for i in (2,1,0):
        await pg.evaluate(TAP,i); await pg.wait_for_timeout(5000)
        for st,d,r in EXP[i]:
          row=await pg.evaluate(ROW,st); ck(row and d in row and (r is None or r in row),f"{eng} y{i} {st} row = official {d} {r or ''}: {row}",row)
        for nm,v in EXACT[str(i)].items():
          g=await pg.evaluate("([st,yr])=>{const v=window.__scopeValsDbg({kind:'sum',st:st},yr); return v&&[v.dem,v.rep,v.tot]}",[ '' if nm=='US' else nm, ['2016','2020','2024'][i]])
          ck(g==v,f"{eng} y{i} {nm}: scope numbers = the official table exactly {g} vs {v}",[g,v])
        th=await pg.evaluate(TH); us=EXACT[str(i)]['US']; exp=[f"{us[0]/1e6:.2f}M",f"{us[1]/1e6:.2f}M"]
        ck(all(x in th for x in exp),f"{eng} y{i} All States thumbnails = official national {exp}: {th}",th)
      ck(not er,f"{eng}: no page errors",er); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
