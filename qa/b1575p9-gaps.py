import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
LI="()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').trim().slice(0,60)).slice(0,8)"
ST="()=>({st:state.value,co:county.value,ph:document.getElementById('gq').placeholder,crumb:document.getElementById('crumbs').innerText.replace(/\\n/g,' '),z:map.getZoom(),lv:window.__laInfo().on?window.__laInfo().lv:'-',lt:__stateSnapshot().lt,list:document.body.classList.contains('listmode')})"
async def fresh(b,eng='chromium',W=390,H=844):
  c,pg,log=await ctx(b,W,H,True,eng); await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000); return c,pg,log
async def typegq(pg,q):
  xy=await center(pg,'#gq'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(600); await pg.keyboard.type(q,delay=25); await pg.wait_for_timeout(2500)
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    # a) address suggestion tap
    c,pg,log=await fresh(b); await typegq(pg,"1600 Pennsylvania Ave NW, Washington, DC 20500")
    out['addr_sugg']=await pg.evaluate(LI)
    xy=await pg.evaluate("()=>{const l=[...document.querySelectorAll('li')].filter(e=>e.offsetParent&&/Address/.test(e.innerText))[0];if(!l)return null;const r=l.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
    if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(7000)
    out['addr_tap']=await pg.evaluate(ST); out['addr_pop']=await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.slice(0,200))")
    await pg.screenshot(path="../shots/b1575p9-ch-390-addr-tap.png")
    # second address (non-DC)
    await typegq(pg,"350 5th Ave, New York, NY 10118"); out['addr2_sugg']=await pg.evaluate(LI)
    await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000); out['addr2_enter']=await pg.evaluate(ST); await pg.screenshot(path="../shots/b1575p9-ch-390-addr2-enter.png")
    out['log_a']={k:v for k,v in log.items() if v}; await c.close()
    # e) other searches in geo field
    for q in ("16501","Pittsburgh","Erie County","PA","Ohio","Cook County, IL"):
      c,pg,log=await fresh(b); await typegq(pg,q); s=await pg.evaluate(LI); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
      out['geo:'+q]={'sugg':s,'after':await pg.evaluate(ST),'err':log['pageerr']}; await pg.screenshot(path=f"../shots/b1575p9-ch-390-geo-{q.replace(' ','').replace(',','')}.png"); await c.close()
    # universal search button
    for q in ("Kamala","Erie","PA-07","Allegheny"):
      c,pg,log=await fresh(b); xy=await center(pg,'#bSearch'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(900)
      await pg.keyboard.type(q,delay=25); await pg.wait_for_timeout(2000); s=await pg.evaluate(LI)
      await pg.screenshot(path=f"../shots/b1575p9-ch-390-search-{q}.png")
      await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500); out['search:'+q]={'sugg':s,'after':await pg.evaluate(ST),'err':log['pageerr']}; await c.close()
    # b) district lists via institution menu at US level
    for k,lab in (('senate','State senate districts'),('house','State house districts'),('school','School districts')):
      c,pg,log=await fresh(b); await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      xy=await pg.evaluate("l=>{const e=[...document.querySelectorAll('li')].find(e=>e.offsetParent&&e.innerText.replace(/^[SH]\\n?/,'').trim()===l);if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",lab)
      R={}
      if xy:
        R['lat_open']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
      R['lvl1']=await pg.evaluate("()=>[window.__laInfo().lv,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).length,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | '))]"); R['st1']=await pg.evaluate(ST)
      await pg.screenshot(path=f"../shots/b1575p9-ch-390-{k}-l1.png")
      for lvl,name in (('l2','PA'),('l3',None),('l4',None)):
        xy=await pg.evaluate("n=>{const rs=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent);const r=n?rs.find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n}):rs[0];if(!r)return null;r.scrollIntoView({block:'center'});const x=r.querySelector('.nmx')||r;const q=x.getBoundingClientRect();return [q.left+q.width/2,q.top+q.height/2]}",name)
        if not xy: R[lvl]='no row'; break
        await pg.wait_for_timeout(400); R['lat_'+lvl]=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
        R[lvl]=await pg.evaluate("()=>[window.__laInfo().lv,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).length,[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | '))]")
        R['st_'+lvl]=await pg.evaluate(ST); await pg.screenshot(path=f"../shots/b1575p9-ch-390-{k}-{lvl}.png")
      R['err']=log['pageerr']+log['console']; out['dist:'+k]=R; await c.close()
    # c) popup vs list: Erie County PA, # mode
    c,pg,log=await fresh(b); await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1000)
    await typegq(pg,"Erie County, PA"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(195,480); await pg.wait_for_timeout(1500)
    out['pop_erie']=await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.slice(0,250))")
    out['data_erie']=await pg.evaluate("()=>ELECTION2024['Pennsylvania|Erie County']")
    await pg.screenshot(path="../shots/b1575p9-ch-390-popup-erie.png")
    # d) double tap
    z0=await pg.evaluate("()=>map.getZoom()"); await pg.touchscreen.tap(150,600); await pg.wait_for_timeout(120); await pg.touchscreen.tap(150,600); await pg.wait_for_timeout(2500)
    out['dbltap']={'z0':z0,'after':await pg.evaluate(ST)}; await pg.screenshot(path="../shots/b1575p9-ch-390-dbltap.png")
    # list view numbers for Erie county row (PA counties list, # mode)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    out['menu_after_county']=await pg.evaluate(LI)
    out['log_c']={k:v for k,v in log.items() if v}; await c.close()
    await b.close()
  json.dump(out,open('b1575p9-gaps.json','w'),indent=1)
  for k,v in out.items(): print(k,':',json.dumps(v)[:700])
if __name__=="__main__": asyncio.run(main())
