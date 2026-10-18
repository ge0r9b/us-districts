import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from gaps import fresh,typegq,ST,LI
ROWS="()=>[window.__laInfo().lv,[...document.querySelectorAll('#listView .lvrow.la')].length,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | '))]"
FIND="n=>{const rs=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent);const r=n?rs.find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n}):rs[0];if(!r)return null;r.scrollIntoView({block:'center'});const q=(r.querySelector('.nmx')||r).getBoundingClientRect();return [q.left+q.width/2,q.top+q.height/2]}"
async def main():
  eng=sys.argv[1]; o={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    c,pg,log=await fresh(b,eng); o['build']=await pg.evaluate("()=>BUILD")
    o['slider']=await pg.evaluate("()=>{const s=document.getElementById('yslider');return [s.min,s.max,s.value,window.__ymode()]}")
    await typegq(pg,"1600 Pennsylvania Ave NW, Washington, DC 20500"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(8000)
    o['QA004_wh_enter']=await pg.evaluate(ST); await pg.screenshot(path=f"../shots/b1569-{eng[:2]}-390-addr-wh-enter.png")
    await typegq(pg,"350 5th Ave, New York, NY 10118"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(8000)
    o['QA004_nyc_enter']=await pg.evaluate(ST); await c.close()
    if eng=='webkit': print(json.dumps(o,indent=0)); return
    # plain states list WY/ND
    async def states_for(lab):
      c,pg,log=await fresh(b,eng)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      if lab:
        await pg.evaluate("l=>[...document.querySelectorAll('li')].find(e=>e.offsetParent&&e.innerText.includes(l)).click()",lab); await pg.wait_for_timeout(4000)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
      vals=await pg.evaluate("()=>{const o={};for(const r of document.querySelectorAll('#listView .lvrow.la')){const n=r.querySelector('.nmx');if(n&&['WY','ND','PA','CA'].includes(n.textContent.trim()))o[n.textContent.trim()]=r.innerText.replace(/\\n/g,' | ')}return o}")
      return c,pg,log,vals
    for lab in (None,'State senate districts','State house districts','School districts'):
      c,pg,log,vals=await states_for(lab); o['QA017 '+str(lab)]=vals
      if lab=='State house districts':
        R=[]
        for name in ('PA',None,None):
          xy=await pg.evaluate(FIND,name)
          if not xy: break
          await pg.wait_for_timeout(300); lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
          R.append([name,'lat',lat]+await pg.evaluate(ROWS))
          await pg.screenshot(path=f"../shots/b1569-ch-390-house-l{len(R)+1}.png")
        o['house_drill']=R
        # drill timing first-frame + rows-change for PA under house, repeat back->PA 3x
      await c.close()
    # QA-005
    c,pg,log=await fresh(b,eng)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    for n in ('PA','Allegheny'):
      xy=await pg.evaluate(FIND,n); await pg.wait_for_timeout(300); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    o['QA005_before']=await pg.evaluate(ROWS)
    xy=await center(pg,'#bLyr'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
    xy=await center(pg,'#lyrRow .lbtn[data-k=ushouse]'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    o['QA005_after']=await pg.evaluate(ROWS); o['QA005_state']=await pg.evaluate(ST)
    o['QA005_crumb_cands']=await pg.evaluate("()=>[...document.querySelectorAll('.cpanel')].map(e=>e.innerText.replace(/\\n/g,' | ').slice(0,120))")
    await pg.screenshot(path="../shots/b1569-ch-390-qa005-ushouse.png"); await c.close()
    # QA-018
    c,pg,log=await fresh(b,eng)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()==='OH'});r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+q.width*0.55,q.top+q.height/2]}")
    await pg.wait_for_timeout(400); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(4000)
    o['QA018_bar_tap']=await pg.evaluate("()=>window.__laInfo().lv+' '+state.value")
    # 2016 check
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
    await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.min;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(3000)
    o['y2016']=await pg.evaluate("()=>({ym:window.__ymode(),rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | ')),cands:[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')+' '+b.innerText.trim())})")
    await pg.screenshot(path="../shots/b1569-ch-390-2016-list.png")
    o['errs']=log['pageerr']+log['console']; await c.close()
    await b.close()
  print(json.dumps(o,indent=0))
asyncio.run(main())
