# b1577: re-test QA-043/047/048/049/050/051, chart-menu rules, '16 line plot, institution field, QA-041. Helpers from b1574-range.py.
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

PTS={'CO':[39.0,-105.5],'KS':[38.5,-98.4],'IL':[40.0,-89.2],'TX':[31.3,-99.3],'FL':[28.3,-81.7],'UT':[39.3,-111.7],'GA':[32.7,-83.4],'PA':[40.9,-77.6],'NY':[42.9,-75.5]}
LBL="()=>[...document.querySelectorAll('.cand,[aria-label]')].filter(e=>e.offsetParent&&/Trump|Harris|Biden|Clinton/.test(e.getAttribute('aria-label')||'')).map(e=>[e.getAttribute('aria-label'),e.title||'',(e.querySelector('.cpt')||e).innerText.replace(/\\n/g,' ').trim(),e.querySelector('img')?(e.querySelector('img').getAttribute('src')||'').split('/').pop().split('?')[0]:''])"
async def menu_opts(pg):
  l=await tapsel(pg,'#chartBox .cmain'); await pg.wait_for_timeout(1200)
  st=await pg.evaluate("()=>({opts:[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch),main:document.querySelector('#chartBox .cmain').dataset.ch,mode:window.chartMode})")
  await pg.evaluate("()=>{const d=document.getElementById('chartDim');d&&d.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))}"); await pg.wait_for_timeout(800)
  return st
async def pix(pg,f):
  xy=await pg.evaluate("P=>{const o={};for(const[k,v] of Object.entries(P)){const q=window.__map.latLngToContainerPoint(v);o[k]=[Math.round(q.x),Math.round(q.y)]}return o}",PTS)
  await pg.screenshot(path=f)
  from PIL import Image
  im=Image.open(f).convert('RGB'); W,H=im.size
  return {k:im.getpixel((v[0]*2,v[1]*2)) for k,v in xy.items() if 0<=v[0]*2<W and 0<=v[1]*2<H}
async def part_us(pg,eng,size,pre,R):
  W=CFG[size][0]
  await open_time(pg); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2000)
  await pg.evaluate("z=>{window.__map.setView([38.5,-96],z,{animate:false});return 1}",4 if W>600 else 3); await pg.wait_for_timeout(5000)
  R['menu_range_20_24']=await menu_opts(pg)
  R['px_20_24']=await pix(pg,pre+'-US-20-24.png'); R['ysl_20_24']=await pg.evaluate("()=>window.__ysl.get()")
  lat=await drag(pg,eng,1,0); await pg.wait_for_timeout(12000)
  R['ysl_16_24']=await pg.evaluate("()=>window.__ysl.get()"); R['px_16_24']=await pix(pg,pre+'-US-16-24.png'); R['lbl_16_24']=await pg.evaluate(LBL)
  R['menu_range_16_24']=await menu_opts(pg)
  await pg.evaluate("()=>window.__ySet16(1)"); await pg.wait_for_timeout(12000)
  R['ysl_16_20']=await pg.evaluate("()=>window.__ysl.get()"); R['px_16_20']=await pix(pg,pre+'-US-16-20.png'); R['lbl_16_20']=await pg.evaluate(LBL)
  await rl(pg); await pg.wait_for_timeout(12000); R['reload_16_20']={'ysl':await pg.evaluate("()=>window.__ysl.get()"),'lbl':await pg.evaluate(LBL)}; await safeshot(pg,pre+'-US-16-20-reload.png')
  await open_time(pg); await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(10000)
  await pg.evaluate("z=>{window.__map.setView([38.5,-96],z,{animate:false});return 1}",4 if W>600 else 3); await pg.wait_for_timeout(4000)
  R['px_2016']=await pix(pg,pre+'-US-2016.png'); R['menu_2016']=await menu_opts(pg)
async def states_list(pg):
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
async def part_line(pg,eng,size,pre,R):
  await states_list(pg); await open_time(pg); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
  R['menu_2024_single']=None
  lat=await drag(pg,eng,1,0); await pg.wait_for_timeout(4000)
  R['after_drag']=await pg.evaluate(PAGE); await safeshot(pg,pre+'-r16-24-afterdrag.png')
  R['line']=await pick_chart(pg,'line'); R['line_page']=await pg.evaluate(PAGE); R['line_all']=await pg.evaluate(ALLROWS); await safeshot(pg,pre+'-r16-24-line.png')
  R['line_svg']=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(e=>/^PA|^FL|^CO|^NY|^TX/.test(e.innerText.trim()));return r.map(e=>({t:e.innerText.replace(/\\n/g,' | '),svg:(e.querySelector('svg')||{outerHTML:''}).outerHTML.slice(0,900)}))}")
  await rl(pg); await pg.wait_for_timeout(12000); R['line_reload']=await pg.evaluate(PAGE); await safeshot(pg,pre+'-r16-24-line-reload.png')
  await open_time(pg); await pg.evaluate("()=>window.__ySet16(1)"); await pg.wait_for_timeout(5000)
  R['line_16_20']=await pg.evaluate(PAGE); await safeshot(pg,pre+'-r16-20-line.png')
  R['line_16_20_all']=await pg.evaluate(ALLROWS)
  R['bar']=await pick_chart(pg,'bar'); R['bar_16_20']=await pg.evaluate(PAGE); R['lbl_states_16_20']=await pg.evaluate(LBL); await safeshot(pg,pre+'-r16-20-states.png')
  # QA-041 Line pick timing in 2020>2024
  await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(4000)
  R['menu_range_list']=await menu_opts(pg)
  t=[]
  for k in range(3):
    a=await pick_chart(pg,'line'); t.append(a.get('lat_pick')); await pick_chart(pg,'bar')
  R['qa041_line_lat']=t
  # one-year menu
  await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(4000); R['menu_2016_list']=await menu_opts(pg)
async def part_prec(pg,eng,size,pre,R):
  await states_list(pg); await open_time(pg); await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(5000)
  await tapname(pg,'PA'); await pg.wait_for_timeout(7000)
  await tapname(pg,'Philadelphia'); await pg.wait_for_timeout(8000)
  lat=await tapname(pg,'Philadelphia city'); await pg.wait_for_timeout(12000)
  R['prec_16_24']=await pg.evaluate(PAGE); R['prec_lbl']=await pg.evaluate(LBL); R['prec_all']=(await pg.evaluate(ALLROWS))[:40]; await safeshot(pg,pre+'-prec-16-24.png')
  await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(2000); R['prec_num']=await pg.evaluate(PAGE); await safeshot(pg,pre+'-prec-16-24-num.png')
  await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500)
  await pg.evaluate("()=>window.__ySet16(1)"); await pg.wait_for_timeout(8000); R['prec_16_20']=await pg.evaluate(PAGE); R['prec_lbl_16_20']=await pg.evaluate(LBL); await safeshot(pg,pre+'-prec-16-20.png')
  await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(8000)
  await rl(pg); await pg.wait_for_timeout(15000); R['prec_reload']=await pg.evaluate(PAGE); await safeshot(pg,pre+'-prec-16-24-reload.png')
SEARCH="(q)=>{const i=document.querySelector('#barGeo .fsq input');if(!i)return 'noinput';i.focus();i.value=q;i.dispatchEvent(new Event('input',{bubbles:true}));return 1}"
ROWS="()=>{const s=document.getElementById('sheet')||document.body;const L=[...s.querySelectorAll('li')].filter(e=>e.offsetParent&&e.innerText.trim());return {n:L.length,first:L.slice(0,6).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40)),none:!!document.querySelector('.orgnone'),body:document.body.className.slice(0,120)}}"
async def part_inst(pg,eng,size,pre,R):
  out=R['inst']={}
  async def probe(level):
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    o=out[level]={'open':await pg.evaluate(ROWS)}
    for q in ['','US','America','penn','phila','cook','ontario','zzqx']:
      o[q or 'empty']=await pg.evaluate(SEARCH,q); await pg.wait_for_timeout(900); o[q or 'empty']=await pg.evaluate(ROWS)
    await safeshot(pg,pre+f'-inst-{level}-zzqx.png')
    await pg.evaluate(SEARCH,'penn'); await pg.wait_for_timeout(900); await safeshot(pg,pre+f'-inst-{level}-penn.png')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>{if(document.body.classList.contains('foldfs'))document.getElementById('bGeo').click()}"); await pg.wait_for_timeout(1000)
  await probe('US')
  await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.dispatchEvent(new Event('change',{bubbles:true}));return 1}"); await pg.wait_for_timeout(5000)
  await probe('PA')
  # Enter takes the top match
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  await pg.evaluate(SEARCH,'ohio'); await pg.wait_for_timeout(900); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
  out['enter_ohio']={'crumbs':await pg.evaluate("()=>document.getElementById('crumbs').innerText"),'state':await pg.evaluate("()=>document.getElementById('state').value")}
  await safeshot(pg,pre+'-inst-enter-ohio.png')
async def run(eng,size,parts):
  W,H,mob=CFG[size]; R={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for part in parts:
      c,pg,log=await ctx(b,W,H,mob,eng); pre=f"../shots/b1581p13-{eng[:2]}-{size}"
      X=R[part]={}
      try:
        await gt(pg); await pg.wait_for_timeout(4000); X['build']=await pg.evaluate("window.BUILD")
        await globals()['part_'+part](pg,eng,size,pre,X)
      except Exception as e: X['EXC']=str(e)[:300]
      X['err']=log['pageerr'][:6]+[x for x in log['console'] if x.startswith('error')][:4]
      print(eng,size,part,'done',X.get('EXC',''),flush=True)
      await c.close()
      json.dump(R,open(f"b1581p13-{eng}-{size}.json",'w'),indent=1)
    await b.close()
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2].split(','); parts=sys.argv[3].split(',') if len(sys.argv)>3 else ['us','line','prec','inst']
  for s in sizes: await run(eng,s,parts)
asyncio.run(main())
