# pass 26: UI-level re-test of the 1599 batch fixes (QA-067, 068, 069, 061, 051), real taps/typing
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
ROWS="()=>{const s=document.getElementById('sheet')||document.body;const L=[...s.querySelectorAll('li')].filter(e=>e.offsetParent&&e.innerText.trim());return L.slice(0,8).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40))}"
LL="()=>[+map.getCenter().lat.toFixed(4),+map.getCenter().lng.toFixed(4),map.getZoom()]"
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}; pre=f"../shots/b1599p26-{eng[:2]}-{W}x{H}"
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    async def fresh():
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); return c,pg,log
    # QA-067
    c,pg,log=await fresh(); out['build']=await pg.evaluate("()=>window.BUILD")
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    xy=await center(pg,'#barGeo .fsq input'); o={}
    for q in ['America','Afrika','penn']:
      if xy: await pg.touchscreen.tap(*xy)
      await pg.keyboard.press('Control+A'); await pg.keyboard.press('Backspace'); await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1500)
      o[q]=await pg.evaluate(ROWS); await safeshot(pg,f"{pre}-inst-{q}.png")
    out['qa067']=o; out['qa067_err']=log['pageerr']; print('067',json.dumps(o),flush=True); await c.close()
    # QA-068 / QA-069
    for k,(a,q) in {'qa069':("Allegheny County, PA","350 5th Ave, New York, NY 10118"),'qa068':("Franklin County, OH","1600 Pennsylvania Ave NW, Washington, DC 20500")}.items():
      c,pg,log=await fresh()
      await typegq(pg,a); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000)
      await typegq(pg,q); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
      s=await pg.evaluate(ST); out[k]={'crumb':s['crumb'],'ph':s['ph'],'st':s['st'],'center':await pg.evaluate(LL),'gq':await pg.evaluate("()=>document.getElementById('gq').value"),'err':log['pageerr']}
      await safeshot(pg,f"{pre}-{k}.png"); print(k,json.dumps(out[k]),flush=True); await c.close()
    # QA-061
    c,pg,log=await fresh()
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    dc=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx')&&r.querySelector('.nmx').textContent.trim()==='DC');if(!r)return null;r.scrollIntoView({block:'center'});const n=r.querySelector('.nmx').getBoundingClientRect();return [n.x+n.width/2,n.y+n.height/2]}")
    await pg.wait_for_timeout(600)
    if dc:
      dc=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent.trim()==='DC');const n=r.querySelector('.nmx').getBoundingClientRect();return [n.x+n.width/2,n.y+n.height/2]}")
      await pg.touchscreen.tap(*dc); await pg.wait_for_timeout(3500)
    s0=await pg.evaluate(ST)
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Delaware';s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(4000)
    s1=await pg.evaluate(ST); out['qa061']={'dc_found':bool(dc),'after_dc':[s0['crumb'],s0['ph']],'after_de':[s1['crumb'],s1['ph']],'err':log['pageerr']}
    await safeshot(pg,f"{pre}-qa061-DE.png"); print('061',json.dumps(out['qa061']),flush=True); await c.close()
    # QA-051
    c,pg,log=await fresh()
    await pg.evaluate("()=>window.__ySet16(1)"); await pg.wait_for_timeout(3000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(6000)
    out['qa051']={'labels':await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.getAttribute('aria-label')+' / '+(b.title||''))"),'text':await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.innerText.replace(/\\n/g,' '))"),'err':log['pageerr']}
    await safeshot(pg,f"{pre}-qa051.png"); print('051',json.dumps(out['qa051']),flush=True); await c.close()
  json.dump(out,open(f'b1599p26-batch-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
