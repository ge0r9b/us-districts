# b1574: re-test of ranges starting at '16 ('16>'20, '16>'24) at US / All States / PA counties / Philadelphia city precincts
import asyncio,json,sys,time
from playwright.async_api import async_playwright
from common import *
CFG={'390':(390,844,True),'320':(320,568,True),'1024x768':(1024,768,False)}
PAGE="""()=>{const q=s=>document.querySelector(s);const vis=e=>e&&e.offsetParent;
 return {ym:window.__ymode(),y16:!!window.__y16,hi:window.__y16hi||0,ysl:window.__ysl.get(),chart:window.chartMode||null,num:window.__numMode&&window.__numMode(),
 view:document.body.classList.contains('listmode')?'list':'map',lv:window.__laInfo().on?window.__laInfo().lv:'-',body:document.body.className,
 ynote:(q('#ynote')||{}).textContent,legend:[...document.querySelectorAll('.heatlbl')].filter(vis).map(e=>e.innerText.replace(/\\n/g,' ')).join(' / '),
 cands:[...document.querySelectorAll('[aria-label]')].filter(e=>vis(e)&&/Trump|Harris|Biden|Clinton/.test(e.getAttribute('aria-label'))).map(e=>e.getAttribute('aria-label')+' ['+e.innerText.replace(/\\n/g,' ').trim()+']').slice(0,4),
 candImgs:[...document.querySelectorAll('img')].filter(e=>vis(e)&&/Trump|Harris|Biden|Clinton|trump|harris|biden|clinton/.test((e.alt||'')+(e.src||''))).map(e=>(e.alt||'')+' '+(e.src||'').split('/').pop().slice(0,40)).slice(0,4),
 opts:[...document.querySelectorAll('#chartBox .copts button')].map(b=>b.dataset.ch),cmain:(q('#chartBox .cmain')||{dataset:{}}).dataset.ch,
 crumbs:(q('#crumbs')||{}).innerText,cpanel:(()=>{const c=q('.cpanel');return c&&vis(c)?c.innerText.replace(/\\n/g,' ').slice(0,200):null})(),
 nrows:[...document.querySelectorAll('#listView .lvrow.la')].length,
 rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(vis).slice(0,8).map(r=>r.innerText.replace(/\\n/g,' | ').slice(0,100)),
 cls:+(window.__cls||0).toFixed(4)}}"""
ALLROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>r.innerText.split('\\n').map(s=>s.trim()).filter(Boolean))"
BARHTML="()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.offsetParent);if(!r)return null;const kids=[...r.children].map(k=>k.className+':'+k.children.length);const svg=r.querySelector('svg,canvas,.lbar,.bar,.sb');return {kids,bar:svg?svg.outerHTML.slice(0,400):r.lastElementChild.outerHTML.slice(0,400)}}"
async def rl(pg):
  try: await pg.reload(wait_until="load",timeout=60000)
  except Exception as e: await pg.wait_for_timeout(3000)
  await pg.wait_for_function("()=>window.__ymode&&window.__ysl&&window.__laInfo",timeout=60000)
async def gt(pg):
  await pg.goto(URL,wait_until="load",timeout=60000); await pg.wait_for_function("()=>window.__ymode&&window.__ysl&&window.__laInfo",timeout=60000)
async def track(pg):
  return await pg.evaluate("()=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return {l:r.left,w:r.width,y:r.top+r.height/2,N}}")
async def open_time(pg):
  await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(900)
async def watch(pg):
  await pg.evaluate("""()=>{window.__wl={up:null,last:null,first:null};const lv=document.getElementById('listView')||document.body;
   if(window.__wmo)window.__wmo.disconnect();window.__wmo=new MutationObserver(()=>{const t=performance.now();if(window.__wl.up!=null){if(window.__wl.first==null)window.__wl.first=t;window.__wl.last=t}});window.__wmo.observe(lv,{subtree:true,childList:true,characterData:true});
   document.addEventListener('pointerup',e=>{window.__wl.up=e.timeStamp||performance.now()},{capture:true,once:true});}""")
async def watched(pg):
  await pg.wait_for_timeout(2500); v=await pg.evaluate("()=>{const w=window.__wl;return w&&w.up!=null?{first:w.first&&Math.round(w.first-w.up),last:w.last&&Math.round(w.last-w.up)}:null}"); return v
async def drag(pg,eng,i0,i1):
  t=await track(pg); x=lambda i:t['l']+52+i/(t['N']-1)*(t['w']-104); y=t['y']
  await watch(pg)
  if eng=='chromium':
    cdp=await pg.context.new_cdp_session(pg)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x(i0),'y':y,'id':1}]})
    for k in range(1,9):
      await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x(i0)+(x(i1)-x(i0))*k/8,'y':y,'id':1}]}); await pg.wait_for_timeout(16)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]}); await cdp.detach()
  else:
    await pg.evaluate("""([a,b,y])=>new Promise(res=>{const w=document.querySelector('.kn.a').parentElement;const ev=(t,cx)=>w.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:7,pointerType:'touch',isPrimary:true,clientX:cx,clientY:y}));
      ev('pointerdown',a);let k=0;const f=()=>{k++;ev('pointermove',a+(b-a)*k/8);if(k<8)requestAnimationFrame(f);else{ev('pointerup',b);res(1)}};requestAnimationFrame(f)})""",[x(i0),x(i1),y])
  return await watched(pg)
async def set_range(pg,eng,hi):
  # start from the 2020>2024 range, then drag one knob to '16 (hi=2: left knob '20->'16; hi=1: right knob '24->'16)
  await open_time(pg)
  if window_state:=await pg.evaluate("()=>window.__ysl.get()"):
    if window_state!=[1,2]: await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
  lat=await drag(pg,eng,1,0) if hi==2 else await drag(pg,eng,2,0)
  await pg.wait_for_timeout(3500)
  st=await pg.evaluate("()=>window.__ysl.get()")
  return st,lat
async def tapsel(pg,sel):
  xy=await center(pg,sel); 
  if not xy: return None
  return await tap_latency(pg,*xy)
async def tapname(pg,n,exact=True):
  xy=await pg.evaluate("([n,ex])=>{const r=[...document.querySelectorAll('#listView .lvrow.la .nmx')].find(x=>ex?x.textContent.trim()===n:x.textContent.includes(n));if(!r)return null;r.scrollIntoView({block:'center'});const b=r.getBoundingClientRect();return [b.left+Math.min(b.width/2,30),b.top+b.height/2]}",[n,exact])
  if not xy: return None
  await pg.wait_for_timeout(400); return await tap_latency(pg,*xy)
async def pick_chart(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return {'already':k}
  l1=await tapsel(pg,'#chartBox .cmain'); await pg.wait_for_timeout(1200)
  st=await pg.evaluate("()=>({opts:[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch),main:document.querySelector('#chartBox .cmain').dataset.ch})")
  sel=f'#chartBox .copts button[data-ch={k}]' if k in st['opts'] else ('#chartBox .cmain' if st['main']==k else None)
  l2=await tapsel(pg,sel) if sel else None
  if l2 is None: await pg.evaluate("()=>{const d=document.getElementById('chartDim');d&&d.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))}")
  await pg.wait_for_timeout(2500); return {'offered':st['opts']+[st['main']],'lat_menu':l1,'lat_pick':l2,'chart_after':await pg.evaluate("()=>window.chartMode"),'ysl_after':await pg.evaluate("()=>window.__ysl.get()")}
async def ensure(pg,hi):
  if (await pg.evaluate("()=>window.__ysl.get()"))!=[0,hi]: await pg.evaluate(f"()=>window.__ySet16({hi})"); await pg.wait_for_timeout(3500); return 'reset'
  return 'ok'
async def run(eng,size,hi):
  W,H,mob=CFG[size]; tagr=f"16-{'24' if hi==2 else '20'}"; R={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,mob,eng)
    pre=f"../shots/b1574-{eng[:2]}-{size}-r{tagr}"
    await gt(pg); await pg.wait_for_timeout(4000)
    R['build']=await pg.evaluate("window.BUILD")
    print('  at','---- US level',flush=True)
    # ---- US level
    await open_time(pg); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
    R['US20']=await pg.evaluate(PAGE)
    lat=await drag(pg,eng,1,0) if hi==2 else await drag(pg,eng,2,0); await pg.wait_for_timeout(3500)
    R['US']={'slider_lat':lat,'page':await pg.evaluate(PAGE)}; await safeshot(pg,pre+"-US.png")
    await rl(pg); await pg.wait_for_timeout(8000); R['US']['reload']=await pg.evaluate(PAGE)
    await ensure(pg,hi)
    R['US']['line']=await pick_chart(pg,'line'); R['US']['after_line']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-US-line.png")
    R['US']['line_set16']=await ensure(pg,hi); R['US']['line16']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-US-line16.png")
    R['US']['bar']=await pick_chart(pg,'bar'); R['US']['after_bar']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-US-bar.png")
    print('  at','---- All States',flush=True)
    # ---- All States
    await c.close(); c,pg,log2=await ctx(b,W,H,mob,eng); log['pageerr']+=['--ctx2--']
    await gt(pg); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await open_time(pg); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>{window.__cls=0;window.__shifts=[]}")
    lat=await drag(pg,eng,1,0) if hi==2 else await drag(pg,eng,2,0); await pg.wait_for_timeout(3500)
    R['States']={'slider_lat':lat,'page':await pg.evaluate(PAGE),'all':await pg.evaluate(ALLROWS),'barhtml':await pg.evaluate(BARHTML),'shifts_slider':await pg.evaluate("()=>window.__shifts.slice(0,10)")}
    await safeshot(pg,pre+"-states-pct.png")
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1800)
    R['States']['num_all']=await pg.evaluate(ALLROWS); await safeshot(pg,pre+"-states-num.png")
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500)
    await rl(pg); await pg.wait_for_timeout(9000)
    R['States']['reload']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-states-reload.png"); await ensure(pg,hi)
    R['States']['line']=await pick_chart(pg,'line'); R['States']['after_line']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-states-line.png")
    R['States']['line_set16']=await ensure(pg,hi); R['States']['line16']=await pg.evaluate(PAGE); R['States']['line_all']=await pg.evaluate(ALLROWS); await safeshot(pg,pre+"-states-line16.png")
    await rl(pg); await pg.wait_for_timeout(9000); R['States']['reload_line']=await pg.evaluate(PAGE); await ensure(pg,hi)
    R['States']['pie']=await pick_chart(pg,'pie'); R['States']['after_pie']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-states-pie.png")
    R['States']['bar']=await pick_chart(pg,'bar'); R['States']['after_bar']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-states-bar.png")
    await ensure(pg,hi)
    print('  at','---- PA counties',flush=True)
    # ---- PA counties
    await pg.evaluate("()=>{window.__cls=0;window.__shifts=[]}")
    lat=await tapname(pg,'PA'); await pg.wait_for_timeout(7000)
    R['PA']={'tap_lat':lat,'page':await pg.evaluate(PAGE),'all':await pg.evaluate(ALLROWS),'shifts':await pg.evaluate("()=>window.__shifts.slice(0,10)")}
    await safeshot(pg,pre+"-PA-bar.png")
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1800)
    R['PA']['num_page']=await pg.evaluate(PAGE); R['PA']['num_all']=await pg.evaluate(ALLROWS); await safeshot(pg,pre+"-PA-num.png")
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
    await rl(pg); await pg.wait_for_timeout(10000); R['PA']['reload']=await pg.evaluate(PAGE); await ensure(pg,hi)
    R['PA']['line']=await pick_chart(pg,'line'); R['PA']['line_set16']=await ensure(pg,hi); R['PA']['line16']=await pg.evaluate(PAGE); R['PA']['line_all']=await pg.evaluate(ALLROWS); await safeshot(pg,pre+"-PA-line16.png")
    R['PA']['bar']=await pick_chart(pg,'bar'); await ensure(pg,hi)
    print('  at','---- Philadelphia county',flush=True)
    # ---- Philadelphia county -> Philadelphia city precincts
    lat=await tapname(pg,'Philadelphia'); await pg.wait_for_timeout(8000)
    R['PhilaCo']={'tap_lat':lat,'page':await pg.evaluate(PAGE)}; await safeshot(pg,pre+"-phila-towns.png")
    await pg.evaluate("()=>{window.__cls=0;window.__shifts=[]}")
    lat=await tapname(pg,'Philadelphia city'); await pg.wait_for_timeout(10000)
    R['Prec']={'tap_lat':lat,'page':await pg.evaluate(PAGE),'all':(await pg.evaluate(ALLROWS))[:30],'shifts':await pg.evaluate("()=>window.__shifts.slice(0,10)")}
    await safeshot(pg,pre+"-prec-pct.png")
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1800); R['Prec']['num_page']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-prec-num.png")
    await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1200)
    await rl(pg); await pg.wait_for_timeout(12000); R['Prec']['reload']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-prec-reload.png"); await ensure(pg,hi)
    R['Prec']['line']=await pick_chart(pg,'line'); R['Prec']['line_set16']=await ensure(pg,hi); R['Prec']['line16']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-prec-line16.png")
    print('  at','comparison:',flush=True)
    # comparison: same precinct list at '20>'24
    await pick_chart(pg,'bar'); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(5000)
    R['Prec']['cmp20_24']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-prec-cmp20-24.png")
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(5000)
    R['Prec']['cmp16']=await pg.evaluate(PAGE); await safeshot(pg,pre+"-prec-cmp16.png")
    R['err']=log['pageerr']+log2['pageerr']+[x for x in log['console']+log2['console'] if x.startswith('error')][:8]; R['http']=(log['http']+log2['http'])[:8]; R['reqfail']=(log['reqfail']+log2['reqfail'])[:5]
    await c.close(); await b.close()
  return R
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2].split(','); his=[int(x) for x in sys.argv[3].split(',')] if len(sys.argv)>3 else [2,1]
  out={}
  for s in sizes:
    for hi in his:
      k=f"{s}-16-{'24' if hi==2 else '20'}"
      try: out[k]=await run(eng,s,hi)
      except Exception as e: out[k]={'EXC':str(e)[:400]}
      print(k,'done',flush=True)
      json.dump(out,open(f"b1574-range-{eng}-{'_'.join(sizes)}.json",'w'),indent=1)
asyncio.run(main())
