# pass 30 (build 1608): quick status of older open bugs: QA-018 row-bar tap, QA-006 Rockledge, QA-015 reload ll, QA-073 school-district latency, QA-074 same-name school rows
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
ROWXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow')].find(r=>r.offsetParent&&(r.querySelector('.nmx')||{}).textContent&&r.querySelector('.nmx').textContent.trim()==t);if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width*0.55,r.top+r.height/2]}"
SNAP="()=>window.__stateSnapshot?JSON.stringify(window.__stateSnapshot()):null"
CR="()=>(document.getElementById('crumbs')||{}).innerText"
async def main():
  eng=sys.argv[1]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,390,844,True,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    xy=await pg.evaluate(ROWXY,'OH'); await pg.wait_for_timeout(500); xy=await pg.evaluate(ROWXY,'OH')
    hit=await pg.evaluate("([x,y])=>{const e=document.elementFromPoint(x,y);return e?e.tagName+'.'+e.className:null}",xy)
    await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3500)
    out['QA018']={'xy':xy,'hit':hit,'crumbs_after':await pg.evaluate(CR),'first_rows':await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))")}
    await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-390-018-OHbar.png")
    print('018',out['QA018'],flush=True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3500)
    await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Philadelphia'))); await pg.wait_for_timeout(3500)
    rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].map(r=>r.innerText.replace(/\\n/g,' | '))")
    out['QA006']={'n':len(rows),'rockledge':[r for r in rows if 'Rockledge' in r],'crumbs':await pg.evaluate(CR),'first':rows[:3]}
    print('006',out['QA006'],flush=True)
    s1=await pg.evaluate(SNAP); await pg.wait_for_timeout(1500)
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(5000); s2=await pg.evaluate(SNAP)
    out['QA015']={'before':s1,'after':s2,'crumbs_after':await pg.evaluate(CR)}
    print('015',out['QA015'],flush=True)
    await c.close()
    out['QA073']={}; out['QA074']={}
    for stn in ['California','Texas','Pennsylvania','Ohio']:
      c,pg,log=await ctx(b,390,844,True,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.evaluate("n=>{const s=document.getElementById('state');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}))}",stn); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
      xy=await center(pg,'#lyrRow .lbtn[data-k=schools]'); lat=await tap_latency(pg,*xy) if xy else None
      out['QA073'][stn]=lat; await pg.wait_for_timeout(5000)
      if stn in ('Ohio','California'):
        await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(7000)
        rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>(r.querySelector('.nmx')||r).textContent.trim()+' || '+r.innerText.replace(/\\n/g,' | '))")
        names=[r.split(' || ')[0] for r in rows]
        out['QA074'][stn]={'n':len(rows),'dup_names':sorted({n for n in names if names.count(n)>1})[:15],'dup_rows':[r for r in rows if names.count(r.split(' || ')[0])>1][:10]}
        await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-390-schools-{stn}.png")
      print('073/074',stn,lat,out['QA074'].get(stn),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1614p35-other-{eng}-390.json",'w'),indent=1)
asyncio.run(main())
