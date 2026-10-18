# Build 1570: 2016 wired to the lazy v2/data files; county tables from the corrected v2/data copies.
# - nothing 2016 loads until 2016 is picked; then only the file the list needs (states table, then counties on drill-in)
# - the 2016 tap paints the placeholder at once (<150 ms, 4x CPU); values fill in when the file arrives
# - All States, # mode: PA / FL 2016 = FEC (Clinton / Trump); OR 2024 and KS 2020 = the corrected county tables
# - PA counties in 2016 read ELECTION2016; Clinton is the blue (dem) segment, Trump red, like Biden / Harris
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
ROW="""(n)=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent===n||r.querySelector('b.rn').title===n);if(!r)return null;
 return [...r.querySelectorAll('[data-party]')].map(e=>[e.className,e.getAttribute('data-party')])}"""
TAPX="""async(i)=>{const w=document.getElementById('ysl'),t=w.querySelector('.tk[data-i="'+i+'"]').getBoundingClientRect(),x=t.left+t.width/2,y=t.top+t.height/2;
 let t0,res;const done=new Promise(r=>res=r);const mo=new MutationObserver(()=>{mo.disconnect();requestAnimationFrame(()=>{const c=new MessageChannel();c.port1.onmessage=()=>res(performance.now()-t0);c.port2.postMessage(0)})});
 mo.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']});
 t0=performance.now();const o={bubbles:true,clientX:x,clientY:y,pointerId:7,pointerType:'touch',isPrimary:true};w.dispatchEvent(new PointerEvent('pointerdown',o));w.dispatchEvent(new PointerEvent('pointerup',o));setTimeout(()=>res(-1),3000);return Math.round(await done)}"""
LOADED="()=>[...document.scripts].map(s=>s.src).filter(s=>/2016/.test(s)).map(s=>s.split('/').pop().split('?')[0])"
def has(row,cls,txt): return bool(row) and any(cls in c and txt in t for c,t in row)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page()
    er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
    if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
    r=await pg.evaluate(ROW,'OR'); ck(has(r,'dem','(Harris): 1,240,600') and has(r,'rep','(Trump): 919,480'),"OR 2024: Harris 1,240,600 / Trump 919,480",r)
    await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=0;s.dispatchEvent(new Event('input',{bubbles:true}))}"); await pg.wait_for_timeout(4000)
    r=await pg.evaluate(ROW,'KS'); ck(has(r,'dem','(Biden): 570,323') and has(r,'rep','(Trump): 771,406'),"KS 2020: Biden 570,323 / Trump 771,406",r)
    l=await pg.evaluate(LOADED); ck(l==[],"no 2016 file loaded before 2016 is picked",l)
    cdp=await c.new_cdp_session(pg); await cdp.send("Emulation.setCPUThrottlingRate",{"rate":4})
    ms=await pg.evaluate(TAPX,0); await cdp.send("Emulation.setCPUThrottlingRate",{"rate":1})
    ck(0<ms<150,f"2016 tap paints in {ms}ms (<150, 4x CPU)",ms)
    await pg.wait_for_timeout(4000)
    l=await pg.evaluate(LOADED); ck(set(l)<={'ds2016-states.js','election2016.js'} and 'ds2016-states.js' in l,"only the 2016 states table loads for the All States list",l)
    for n,d,rr in (('PA','2,926,441','2,970,733'),('FL','4,504,975','4,617,886'),('MI','2,268,839','2,279,543')):
      r=await pg.evaluate(ROW,n); ck(has(r,'dem','(Clinton): '+d) and has(r,'rep','(Trump): '+rr),f"{n} 2016 = FEC: Clinton {d} (blue, dem) / Trump {rr} (red)",r)
    th=await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>[b.dataset.cid,b.querySelector('.cpt').textContent])")
    ck(len(th)==2 and {x[0] for x in th}=={'c16','t16'} and all(x[1] for x in th),"thumbnails: Clinton + Trump with 2016 figures",th)
    await pg.screenshot(path='/workspace/y2016-data-states.png')
    # QA-031 / QA-032: no 'not loaded' note; rows sort by 2016 values; internal year 2016; reload restores '16
    ck(not await pg.evaluate("()=>/No 2016 results|not ready/.test(document.body.innerText)"),"QA-031: no 'No 2016 results' / 'not ready' note")
    od=await pg.evaluate("""()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,6).map(r=>{const e=[...r.querySelectorAll('[data-party]')].find(x=>/dem/.test(x.className)&&/Clinton/.test(x.getAttribute('data-party')));const t=e?e.getAttribute('data-party'):'';const m=/Clinton\\): ([\\d,]+)/.exec(t);return [r.querySelector('.nmx').textContent,m?+m[1].replace(/,/g,''):null]})""")
    ck(len(od)>=5 and all(x[1] is not None for x in od) and all(od[i][1]>=od[i+1][1] for i in range(len(od)-1)) and od[0][0]=='CA',"QA-032: rows sort by 2016 Clinton votes (CA first)",od)
    ck(await pg.evaluate("()=>window.ym&&ym()")=="2016" or await pg.evaluate("()=>window.__y16&&!window.__y16hi"),"QA-032: internal year is 2016")
    await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(300)
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
    ck(await pg.evaluate("()=>!!window.__y16&&!window.__y16hi&&document.body.classList.contains('y16')"),"QA-032: reload restores '16")
    r=await pg.evaluate(ROW,'PA'); ck(has(r,'dem','(Clinton): 2,926,441'),"after reload PA shows 2016 Clinton",r)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(8000)
    await pg.screenshot(path='/workspace/y16drill.png'); print(await pg.evaluate("()=>[document.getElementById('crumbs').textContent,document.querySelectorAll('#listView .lvrow').length,document.body.className]"))
    l=await pg.evaluate(LOADED); ck('election2016.js' in l,"drill-in to PA counties loads election2016.js",l)
    e=await pg.evaluate("()=>window.ELECTION2016&&window.ELECTION2016['Pennsylvania|Philadelphia County']")
    r=await pg.evaluate(ROW,'Philadelphia County'); fm=lambda n:f"{n:,}"
    ck(e and has(r,'dem','(Clinton): '+fm(e[0])) and has(r,'rep','(Trump): '+fm(e[1])),"PA counties 2016: Philadelphia = ELECTION2016",[e,r])
    await pg.evaluate(TAPX,2); await pg.wait_for_timeout(4000)
    r=await pg.evaluate(ROW,'Philadelphia County'); ck(has(r,'dem','(Harris)'),"back to 2024 shows Harris again",r)
    # map view: 2016 shapes are drawn (never a blank map)
    c2=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); p2=await c2.new_page(); p2.on('pageerror',lambda e:er.append(str(e)))
    await p2.goto(U,wait_until="networkidle"); await p2.wait_for_timeout(3500)
    await p2.evaluate("()=>window.__ySet16(0)"); await p2.wait_for_timeout(5000)
    px=await p2.evaluate("""()=>{const cs=[...document.querySelectorAll('.leaflet-pane canvas')];let n=0,col=new Set();cs.forEach(cv=>{try{const g=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;for(let i=0;i<g.length;i+=4*97){if(g[i+3]>100){n++;col.add(g[i]>>4<<8|g[i+1]>>4<<4|g[i+2]>>4)}}}catch(e){}});return [n,col.size,document.body.classList.contains('noplot')]}""")
    ck(px[0]>2000 and px[1]>10 and not px[2],"2016 map: state / county shapes drawn with colours (not blank)",px)
    await p2.screenshot(path='/workspace/y2016-map.png'); await c2.close()
    ck(not er,"no page errors",er[:2]); await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
