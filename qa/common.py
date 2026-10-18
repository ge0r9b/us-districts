import asyncio,json,time
URL="https://ge0r9b.github.io/us-districts/v2/"
VPS=[("iphone390",390,844,True),("iphone375",375,667,True),("iphone320",320,568,True),("ipad1024x576",1024,576,False),("ipad1024x768",1024,768,False)]
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
UAI="Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
INIT="""(()=>{window.__cls=0;window.__shifts=[];try{new PerformanceObserver(l=>{for(const e of l.getEntries()){if(!e.hadRecentInput){window.__cls+=e.value;window.__shifts.push({v:+e.value.toFixed(4),t:Math.round(e.startTime),src:(e.sources||[]).map(s=>{const n=s.node;return n?(n.id||n.className||n.nodeName).toString().slice(0,40):'?'})})}}}).observe({type:'layout-shift',buffered:true})}catch(e){}})()"""
async def ctx(b,W,H,mob,engine='chromium'):
    kw=dict(viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True)
    if engine=='chromium': kw['is_mobile']=True  # all targets are touch iOS devices
    kw['user_agent']=UA if W<600 else UAI
    c=await b.new_context(**kw); await c.add_init_script(INIT); pg=await c.new_page()
    log={'console':[],'pageerr':[],'reqfail':[],'http':[]}
    pg.on('console',lambda m: log['console'].append(m.type+': '+m.text[:200]) if m.type in('error','warning') else None)
    pg.on('pageerror',lambda e: log['pageerr'].append(str(e)[:200]))
    pg.on('requestfailed',lambda r: log['reqfail'].append(r.url[:150]+' '+str(r.failure)))
    pg.on('response',lambda r: log['http'].append(str(r.status)+' '+r.url[:150]) if r.status>=400 else None)
    return c,pg,log
# measure tap-to-next-paint: tap at x,y then time until 2 rAFs after the event handlers
TAPLAT="""()=>new Promise(res=>{const t0=performance.now();window.__tl0=t0;res(t0)})"""
async def tap_latency(pg,x,y):
    # install a one-shot listener capturing event timestamp and next-paint
    await pg.evaluate("""()=>{window.__lat=null;const h=e=>{const t0=e.timeStamp;requestAnimationFrame(()=>setTimeout(()=>{window.__lat=performance.now()-t0},0));};let done=false;const g=e=>{if(done)return;done=true;h(e)};['pointerup','touchend','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}));}""")
    await pg.touchscreen.tap(x,y)
    for _ in range(40):
        v=await pg.evaluate("()=>window.__lat")
        if v is not None: return round(v,1)
        await pg.wait_for_timeout(50)
    return None
async def center(pg,sel):
    return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
async def safeshot(pg,path):
    try: await pg.screenshot(path=path,timeout=20000)
    except Exception as e: print('SHOT-TIMEOUT',path,str(e)[:80],flush=True)
