# Speed baseline: startup bytes, first map, tap latency, pan smoothness.
# usage: python3 baseline.py <url> <tag,...|all> <out.json> [noglass] [tries]
import asyncio,json,sys,time,statistics as st
from playwright.async_api import async_playwright
U=sys.argv[1]; WH=sys.argv[2]; OUT=sys.argv[3]
NOGL='noglass' in sys.argv[4:]; TRIES=int(([a for a in sys.argv[4:] if a.isdigit()] or ['5'])[0])
VPS=[("390x844",390,844),("375x667",375,667),("320x568",320,568),("ipad820x1180",820,1180)]
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
UAI="Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
NOGLASS="*,*::before,*::after{-webkit-backdrop-filter:none!important;backdrop-filter:none!important}"
# first-map probe: first rAF where the map shows a drawn vector layer (svg path / canvas in overlay pane) and first loaded tile
INIT="""(()=>{window.__fm={};const chk=()=>{const m=document.getElementById('map');if(m){
 if(!__fm.tile){const t=m.querySelector('.leaflet-tile-loaded');if(t)__fm.tile=performance.now();}
 if(!__fm.vec){for(const cv of m.querySelectorAll('.leaflet-pane canvas, .leaflet-pane path[d]')){ if(cv.tagName==='path'){__fm.vec=performance.now();break;}
   if(!cv.width)continue; const o=window.__fmc||(window.__fmc=document.createElement('canvas'));o.width=o.height=24;const x=o.getContext('2d',{willReadFrequently:true});x.clearRect(0,0,24,24);try{x.drawImage(cv,0,0,24,24);const d=x.getImageData(0,0,24,24).data;for(let i=3;i<d.length;i+=4)if(d[i]){__fm.vec=performance.now();__fm.vecPane=cv.parentElement.className;break;}}catch(e){} if(__fm.vec)break;}}}
 if(!(__fm.tile&&__fm.vec)&&performance.now()<60000)requestAnimationFrame(chk)};requestAnimationFrame(chk);
 try{new PerformanceObserver(l=>{for(const e of l.getEntries())__fm[e.name==='first-contentful-paint'?'fcp':e.name]=e.startTime}).observe({type:'paint',buffered:true});
 new PerformanceObserver(l=>{for(const e of l.getEntries())__fm.lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true});
 window.__lt=[];new PerformanceObserver(l=>{for(const e of l.getEntries())__lt.push([Math.round(e.startTime),Math.round(e.duration)])}).observe({type:'longtask',buffered:true});}catch(e){}
 %s })()"""
REC_START="()=>{window.__fd=[];let l=performance.now();window.__rec=true;const f=t=>{if(!window.__rec)return;window.__fd.push(t-l);l=t;requestAnimationFrame(f)};requestAnimationFrame(f)}"
REC_STOP="()=>{window.__rec=false;return window.__fd.slice(1)}"
ARM="""()=>{window.__lat=null;let done=false;const g=e=>{if(done)return;done=true;const t0=e.timeStamp;requestAnimationFrame(()=>setTimeout(()=>{window.__lat=performance.now()-t0},0))};['pointerup','touchend','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}))}"""
def frames(d):
  if not d: return {}
  s=sorted(d); n=len(d)
  return {"frames":n,"avg_ms":round(sum(d)/n,1),"p95_ms":round(s[max(0,int(n*.95)-1)],1),"max_ms":round(s[-1],1),
          "janky_gt25":sum(1 for x in d if x>25),"dropped":int(sum(max(0,round(x/16.67)-1) for x in d)),"fps":round(1000*n/sum(d),1)}
async def main():
  res={}
  async with async_playwright() as p:
    b=await p.chromium.launch(args=["--enable-precise-memory-info"])
    for tag,W,H in VPS:
      if WH!='all' and tag not in WH.split(','): continue
      c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=True,has_touch=True,user_agent=UA if W<600 else UAI)
      await c.add_init_script(INIT%(("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent=%r;document.head.append(s)});"%NOGLASS) if NOGL else ""))
      pg=await c.new_page(); cdp=await c.new_cdp_session(pg); await cdp.send("Network.enable")
      NET={}; R={'viewport':tag,'lat':{},'notes':[],'errors':[]}
      pg.on('pageerror',lambda e: R['errors'].append(str(e)[:200]))
      def onresp(e): NET.setdefault(e['requestId'],{})['url']=e['response']['url']
      def ondata(e): r=NET.setdefault(e['requestId'],{}); r['dec']=r.get('dec',0)+e['dataLength']
      def onfin(e): r=NET.setdefault(e['requestId'],{}); r['enc']=e['encodedDataLength']
      cdp.on("Network.responseReceived",onresp); cdp.on("Network.dataReceived",ondata); cdp.on("Network.loadingFinished",onfin)
      def netsnap(label):
        rs=[dict(v) for v in NET.values() if 'url' in v]
        app=[r for r in rs if 'ge0r9b.github.io' in r['url'] or 'localhost' in r['url']]
        def tot(L): return {"enc":sum(r.get('enc',0) for r in L),"dec":sum(r.get('dec',0) for r in L),"n":len(L)}
        R['bytes_'+label]={"all":tot(rs),"app":tot(app),"tiles":tot([r for r in rs if '/tile/' in r['url']])}
        R['top10_'+label]=[{"url":r['url'].split('?')[0].replace('https://ge0r9b.github.io/us-districts/',''),"enc":r.get('enc',0),"dec":r.get('dec',0)} for r in sorted(rs,key=lambda r:-r.get('dec',0))[:10]]
      async def center(sel):
        return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width||r.bottom<0||r.top>innerHeight)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
      async def tapxy(x,y):
        await pg.evaluate(ARM); await pg.touchscreen.tap(x,y)
        for _ in range(60):
          v=await pg.evaluate("()=>window.__lat")
          if v is not None: return round(v,1)
          await pg.wait_for_timeout(50)
      async def tap(sel,name,wait=1500):
        xy=await center(sel)
        if not xy: R['notes'].append(f'{name}: {sel} not visible'); await pg.wait_for_timeout(300); return None
        v=await tapxy(*xy); R['lat'].setdefault(name,[]).append(v); await pg.wait_for_timeout(wait); return v
      t0=time.time()
      await pg.goto(U+("&" if "?" in U else "?")+"v=%d"%(time.time()*1000),wait_until="load",timeout=180000)
      try: await pg.wait_for_load_state("networkidle",timeout=60000)
      except Exception: R['notes'].append('networkidle timeout')
      await pg.wait_for_timeout(3000)
      R['timing']=await pg.evaluate("""()=>{const n=performance.getEntriesByType('navigation')[0];const f=window.__fm;return {ttfb:Math.round(n.responseStart),html_done:Math.round(n.responseEnd),dcl:Math.round(n.domContentLoadedEventEnd),load:Math.round(n.loadEventEnd),fcp:Math.round(f.fcp||0),lcp:Math.round(f.lcp||0),first_vector_map:Math.round(f.vec||0),first_tile:Math.round(f.tile||0),first_map:Math.round(Math.max(f.vec||0,f.tile||0)),longtasks_ms:__lt.reduce((a,x)=>a+x[1],0),longest_task:Math.max(0,...__lt.map(x=>x[1])),heapMB:performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null}}""")
      netsnap('initial')
      # --- pan smoothness on the US map (3 drags, ~20 moves each)
      await pg.evaluate(REC_START)
      for i in range(3):
        x0,y0=W*0.3,H*0.5
        await cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":x0,"y":y0}]})
        for k in range(1,25):
          await cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":x0+k*(6 if i%2==0 else -6),"y":y0+k*(3 if i!=1 else -3)}]}); await pg.wait_for_timeout(16)
        await cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]})
        await pg.wait_for_timeout(300)
      R['pan']=frames(await pg.evaluate(REC_STOP))
      # --- All States (institution menu row) x TRIES
      for i in range(TRIES):
        if not await center('li.la-row'): await tap('#bGeo','open_institution',1200)
        if await tap('li.la-row','all_states',3500) is None: break
        if i<TRIES-1: await tap('#bGeo','open_institution',1200)
      await pg.wait_for_timeout(2000)
      try: R.setdefault('map_view',{})['all_states']=await pg.evaluate("()=>{const c=map.getCenter();return [map.getZoom(),+c.lat.toFixed(3),+c.lng.toFixed(3)]}")
      except Exception as e: R['notes'].append('map_view '+str(e)[:80])
      if not await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length"):
        R['notes'].append('no All States list rows')
      # --- time slider step (tap 2020 end <-> 2024 end of the slider track)
      await tap('#bTime','time_open',1200)
      for i in range(TRIES):
        for ti in ('1','2'):
          await tap(f'#ysl .tk[data-i="{ti}"]','time_step',2200)
      await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(2500)
      # --- Line pick (needs a range): range 2020>2024 then chart menu > line / bar alternating
      await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=+s.max-1;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(3000)
      R['ymode_range']=await pg.evaluate("()=>window.__ymode&&window.__ymode()")
      for i in range(TRIES):
        for k in ('line','bar'):
          if not await pg.evaluate("()=>{const b=document.getElementById('chartBox');return !!(b&&b.classList.contains('open'))}"): await tap('#chartBox .cmain','chart_menu',900)
          await tap(f'#chartBox .copts button[data-ch={k}]',f'chart_{k}',1800)
      await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))}"); await pg.wait_for_timeout(3000)
      R['ymode_end']=await pg.evaluate("()=>window.__ymode&&window.__ymode()")
      if await pg.evaluate("()=>!document.getElementById('barTime').hidden"): await tap('#bTime','time_close',1000)
      # --- drill into PA and back x TRIES
      PAXY="()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}"
      for i in range(TRIES):
        xy=await pg.evaluate(PAXY); await pg.wait_for_timeout(500)
        if not xy: R['notes'].append('PA row not found'); break
        xy=await pg.evaluate(PAXY)
        R['lat'].setdefault('drill_PA',[]).append(await tapxy(*xy)); await pg.wait_for_timeout(4000)
        if i<TRIES-1: await tap('#bBack','back',3000)
      try: R.setdefault('map_view',{})['drill_PA']=await pg.evaluate("()=>{const c=map.getCenter();return [map.getZoom(),+c.lat.toFixed(3),+c.lng.toFixed(3)]}")
      except Exception as e: R['notes'].append('map_view '+str(e)[:80])
      R['pa_info']=await pg.evaluate("()=>window.__laInfo&&JSON.stringify(window.__laInfo()).slice(0,160)")
      # --- US House pick inside PA (type menu) x TRIES, alternating pick / deselect
      for i in range(TRIES):
        if not await center('#lyrRow .lbtn[data-k=ushouse]'): await tap('#bLyr','type_menu',1000)
        await tap('#lyrRow .lbtn[data-k=ushouse]','ushouse_pick',3500)
        if i==0: R['pa_ushouse_rows']=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length")
        if not await center('#lyrRow .lbtn[data-k=ushouse]'): await tap('#bLyr','type_menu',1000)
        if i<TRIES-1: await tap('#lyrRow .lbtn[data-k=ushouse]','ushouse_deselect',2500)
      try: await pg.wait_for_load_state("networkidle",timeout=30000)
      except Exception: pass
      await pg.wait_for_timeout(2000)
      netsnap('pa_session')
      R['heapMB_end']=await pg.evaluate("()=>performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null")
      R['lat_summary']={k:{"median":round(st.median([x for x in v if x is not None]),1),"max":max(x for x in v if x is not None),"n":len(v)} for k,v in R['lat'].items() if any(x is not None for x in v)}
      res[tag]=R; await c.close()
      print(tag,json.dumps({'timing':R['timing'],'bytes_initial':R['bytes_initial']['app'],'bytes_pa':R['bytes_pa_session']['app'],'pan':R['pan'],'lat':R['lat_summary'],'notes':R['notes'][:6],'errors':R['errors'][:3]}),flush=True)
    await b.close()
  json.dump(res,open(OUT,'w'),indent=1)
asyncio.run(main())
