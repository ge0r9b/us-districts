# Oct 26 ~9 AM (1622): solo sort-chip latency on a 159-row county list, town list sort/# at '24 (no '16 pick, QA-138), reload restore at the town list, back chain
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))"
NMX="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
CR="()=>[(document.getElementById('crumbs')||{}).innerText,(document.getElementById('vtitle')||{}).innerText,[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ')).join(' / ')]"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; st=sys.argv[3]; cty=sys.argv[4]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"../shots/b1622d26h09-{eng[:2]}-{W}x{H}-deep"
    async def tap(sel,w=1500):
      xy=await center(pg,sel)
      if not xy: return 'nosel'
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
    async def drill(t):
      await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(400)
      xy=await pg.evaluate(NMX,t); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMX,t)
      if not xy: return None
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); return v
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    await tap('#bGeo',1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    out['drill_st']=await drill(st); out['st']=await pg.evaluate(CR)
    out['st_sort']=[await tap('#laSort',1200) for _ in range(4)]
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); out['st_sort_num']=[await tap('#laSort',1200) for _ in range(2)]; await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500)
    out['drill_cty']=await drill(cty); out['cty']=await pg.evaluate(CR); out['cty_rows']=await pg.evaluate(ROWS)
    out['cty_sort']=[await tap('#laSort',1200) for _ in range(2)]; out['cty_rows_after2']=await pg.evaluate(ROWS)
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500); out['cty_num']=await pg.evaluate(ROWS); out['cty_sort_num']=await tap('#laSort',1200); out['cty_num_flip']=await pg.evaluate(ROWS); await tap('#laSort',1200)
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200); await safeshot(pg,pre+'-town.png')
    # deeper: first town
    t1=(out['cty_rows'][0] or '').split(' | ')[0]; out['town_name']=t1; out['drill_town']=await drill(t1); out['town']=await pg.evaluate(CR); out['town_rows']=await pg.evaluate(ROWS); await safeshot(pg,pre+'-town2.png')
    await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); s0=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200)
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
    out['reload']={'before':s0,'after':await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'cr':await pg.evaluate(CR),'rows':await pg.evaluate(ROWS)}; await safeshot(pg,pre+'-reload.png')
    bc=out['back']=[]
    for i in range(4):
      xy=await center(pg,'#bBack') or await center(pg,'#listView .lvback')
      if not xy: bc.append('noback'); break
      lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(3000); bc.append([lat,await pg.evaluate(CR),(await pg.evaluate(ROWS))[:1]])
    await safeshot(pg,pre+'-backend.png')
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]
    print(json.dumps(out,indent=0)[:6000])
    json.dump(out,open(f'b1622d26h09-deep-{eng}-{W}x{H}-{st}.json','w'),indent=1); await b.close()
asyncio.run(main())
