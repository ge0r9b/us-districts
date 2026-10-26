# Oct 26 ~10 AM (1623) copy of d26h09-sortnum.py
# Oct 26 ~9 AM (1622): sort chip default/flip and % vs # at every list level (All States > OH counties > OH US House > Franklin towns), slider ranges on state-level and district lists, chip overlap (CHK), clipped row text, reload restore after deep nav
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
TH="()=>[...document.querySelectorAll('#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' '))"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,5).map(r=>r.innerText.replace(/\\n/g,' | '))"
ALLV="()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>r.innerText.replace(/\\n/g,' | '))"
CLIP="()=>[...document.querySelectorAll('#listView .lvrow.la *, #laCands *, #crumbs, #vtitle')].filter(e=>e.offsetParent&&e.children.length==0&&e.innerText&&(e.scrollWidth>e.clientWidth+1)&&getComputedStyle(e).overflow!='visible').slice(0,6).map(e=>[e.className||e.id,e.innerText.slice(0,30),e.scrollWidth,e.clientWidth])"
NMX="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsb1623/d26h10-{eng[:2]}-{W}x{H}-sn"
    async def tap(sel,w=1500):
      xy=await center(pg,sel)
      if not xy: return 'nosel'
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
    async def snap(L,tag):
      L['crumbs']=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"); L['title']=await pg.evaluate("()=>(document.getElementById('vtitle')||{}).innerText")
      L['ysl']=await pg.evaluate("()=>window.__ysl.get()"); L['th']=await pg.evaluate(TH); L['rows']=await pg.evaluate(ROWS); L['chip']=await pg.evaluate(CHK); L['clip']=await pg.evaluate(CLIP)
      L['sortlbl']=await pg.evaluate("()=>{const s=document.getElementById('laSort');return s&&s.offsetParent?s.innerText+'|'+(s.getAttribute('aria-label')||''):null}")
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1300); L['th_num']=await pg.evaluate(TH); L['rows_num']=await pg.evaluate(ROWS); L['chip_num']=await pg.evaluate(CHK); L['clip_num']=await pg.evaluate(CLIP)
      await safeshot(pg,f'{pre}-{tag}-num.png')
      L['sort_lat']=await tap('#laSort',1300); L['rows_flip']=await pg.evaluate(ROWS); L['sortlbl_flip']=await pg.evaluate("()=>{const s=document.getElementById('laSort');return s&&s.offsetParent?s.innerText:null}")
      L['sort2_lat']=await tap('#laSort',1300); L['rows_back']=await pg.evaluate(ROWS)
      L['num2pct_lat']=None; await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1000)
      await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(300); await safeshot(pg,f'{pre}-{tag}-pct.png')
      print(tag,json.dumps(L)[:3000],flush=True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    await tap('#bTime',800)
    await tap('#bGeo',1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    async def ranges(lvl,allow16=True):
      R=out[lvl+'-ranges']={}
      for nm,js in ([('16-20','window.__ySet16(1)'),('16-24','window.__ySet16(2)')] if allow16 else [])+[('20-24','window.__ySelectAll()'),('y24','window.__ySetYr(2)')]:
        await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(3000); L=R[nm]={}; await snap(L,f'{lvl}-r{nm}')
    import os
    LV=[('states',None)] if not os.environ.get('SKIPST') else []
    for lvl,how in LV+[(sys.argv[3],sys.argv[3]),(sys.argv[4],sys.argv[4])]:
      if how:
        xy=await pg.evaluate(NMX,how); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMX,how)
        if not xy: out[lvl]='notfound'; print(lvl,'notfound',await pg.evaluate(ROWS)); break
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000); await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(500)
      L=out[lvl]={}; await snap(L,lvl)
      if lvl!=sys.argv[4]: await ranges(lvl)
      else: await ranges(lvl,False)
      if lvl==sys.argv[3]:
        # district list: US House in Ohio
        await tap('#bLyr',900); out[lvl+'-ush-lat']=await tap('#lyrRow button[data-k=ushouse]',3500)
        L=out[lvl+'-ushouse']={}; await snap(L,lvl+'-ushouse'); L['all']=await pg.evaluate(ALLV); await ranges(lvl+'-ushouse')
        await tap('#bLyr',900); await tap('#lyrRow button[data-k=ushouse]',3500)
    # reload restore after deep nav
    await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); s0=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); c0=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText")
    await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(8000)
    out['reload']={'before':[c0,s0],'after':[await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"),await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())")],'rows':await pg.evaluate(ROWS),'ysl':await pg.evaluate("()=>window.__ysl.get()")}
    await safeshot(pg,f'{pre}-reload.png')
    # back chain
    bc=out['backchain']=[]
    for i in range(4):
      xy=await center(pg,'#listView .lvback') or await center(pg,'#bBack')
      if not xy: bc.append('noback'); break
      lat=await tap_latency(pg,*xy); await pg.wait_for_timeout(3000)
      bc.append([lat,await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"),(await pg.evaluate(ROWS))[:1]])
    print('reload',json.dumps(out['reload'])[:1500],'back',bc,flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]; print('err',out['err'])
    json.dump(out,open(f'b1623d26h10-sortnum-{eng}-{W}x{H}-{sys.argv[3]}.json','w'),indent=1); await b.close()
asyncio.run(main())
