# Oct 26 ~12 AM (1622) copy of h2300-lay3.py
# Oct 25 ~11 PM (1622) copy of h2200-lay3.py
# Oct 25 ~9 PM (1622) copy of h2000-lay3.py
# Oct 25 5PM (1620) copy of h1620-lay3.py + tap-to-paint (first frame where title/crumbs/first-row/thumb text changes); was: 3PM copy of h1200-lay3.py
# b1574: layout-stability sweep. Records bounding boxes of chrome elements before/after (and every frame during) each view switch, year change, drill-in, back.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
BOX="""()=>{const o={};const add=(k,e)=>{if(!e||!e.offsetParent&&getComputedStyle(e).position!=='fixed')return;const r=e.getBoundingClientRect();if(!r.width||!r.height)return;const cs=getComputedStyle(e);if(cs.visibility==='hidden'||+cs.opacity===0)return;o[k]=[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]};
 for(const id of ['vtitle','crumbs','ysl','gq','bSearch','bGeo','bTime','bLyr','bNum','bGlobe']) add(id,document.getElementById(id));
 add('chartBtn',document.querySelector('#chartBox .cmain'));
 [...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).forEach((e,i)=>add('thumb'+i,e));
 [...document.querySelectorAll('#laCands .lact')].filter(e=>e.offsetParent).forEach((e,i)=>add('lthumb'+i,e)); add('laSort',document.getElementById('laSort'));
 const fr=[...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent); add('firstRow',fr);
 const bk=document.querySelector('#listView .lvback, #listView [aria-label*=ack i], .backbtn, #bBack'); add('back',bk);
 return o}"""
SAMPLE="""(ms)=>new Promise(res=>{const fr=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;fr.push([Math.round(t),(%s)()]);if(t<ms)requestAnimationFrame(f);else res(fr)};requestAnimationFrame(f)})"""%BOX
VISTXT="(t)=>{const L=[...document.querySelectorAll('li,.lvrow,button')].filter(e=>e.offsetParent&&e.innerText);const nm=e=>e.innerText.trim().split('\\n').map(x=>x.replace('›','').trim()).filter(x=>x.length>1)[0]||'';let e=L.filter(e=>nm(e)===t);if(!e.length)e=L.filter(e=>nm(e).startsWith(t));if(!e.length)return null;const r=e[e.length-1];r.scrollIntoView({block:'nearest'});const n=r.querySelector('.nmx')||r;const b=n.getBoundingClientRect();return [b.left+b.width/2,b.top+b.height/2]}"
SIG="()=>{const t=e=>e?e.innerText.slice(0,60):'';const fr=[...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent);return [t(document.getElementById('vtitle')),t(document.getElementById('crumbs')),t(fr),[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>e.innerText).join('|').slice(0,80),document.body.className].join('#')}"
SIGS="""(ms)=>new Promise(res=>{const s0=(%s)();const t0=performance.now();const f=()=>{const t=performance.now()-t0;if((%s)()!==s0)return res(Math.round(t));if(t<ms)requestAnimationFrame(f);else res(null)};requestAnimationFrame(f)})"""%(SIG,SIG)
TH=2
def diff(a,b):
  out=[]
  for k in sorted(set(a)|set(b)):
    if k in a and k in b:
      d=[b[k][i]-a[k][i] for i in range(4)]
      if any(abs(x)>=TH for x in d): out.append({'el':k,'dx':d[0],'dy':d[1],'dw':d[2],'dh':d[3],'before':a[k],'after':b[k]})
    elif k in a: out.append({'el':k,'gone':a[k]})
    else: out.append({'el':k,'new':b[k]})
  return out
def transient(frames,final):
  # positions an element took during the transition that are neither the start nor the final one
  seq={}
  for t,o in frames:
    for k,v in o.items():
      s=seq.setdefault(k,[])
      if not s or s[-1][1]!=v: s.append((t,v))
  return {k:s for k,s in seq.items() if len(s)>2 or (len(s)==2 and final.get(k)!=s[-1][1])}
async def main():
  eng=sys.argv[1]; size=sys.argv[2]; W,H={'1024x768':(1024,768),'1024x576':(1024,576),'390':(390,844),'375':(375,667),'320':(320,568)}[size]
  steps=[]; R={'size':size,'eng':eng,'steps':steps}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__ysl",timeout=60000); await pg.wait_for_timeout(5000)
    R['build']=await pg.evaluate("window.BUILD"); n=[0]
    async def step(name,action,settle=2200):
      try: await _step(name,action,settle)
      except Exception as e: steps.append({'step':name,'EXC':str(e)[:200]}); print('EXC',name,str(e)[:120],flush=True)
    async def _step(name,action,settle=2200):
      n[0]+=1; tag=f"shotsb1622/b1622h02-{eng[:2]}-{size}-ls3{n[0]:02d}-{name}"
      a=await pg.evaluate(BOX); await safeshot(pg,tag+"-before.png")
      samp=asyncio.ensure_future(pg.evaluate(SAMPLE,settle)); sg=asyncio.ensure_future(pg.evaluate(SIGS,settle))
      ok=await action()
      frames=await samp; paint=await sg; await pg.wait_for_timeout(300)
      z=await pg.evaluate(BOX); await safeshot(pg,tag+"-after.png")
      st=await pg.evaluate("()=>({crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),lt:window.__stateSnapshot&&window.__stateSnapshot().lt,lv:window.__laInfo().on?window.__laInfo().lv:'-',ysl:window.__ysl.get()})")
      steps.append({'n':n[0],'step':name,'ok':ok,'state':st,'moved':diff(a,z),'transient':transient(frames,z),'paint_ms':paint,'shots':[tag+"-before.png",tag+"-after.png"]})
      print(n[0],name,ok,'paint',paint,st,'moved',[ (m['el'],m.get('dx'),m.get('dy'),m.get('dw'),m.get('dh')) if 'dx' in m else (m['el'],'gone' if 'gone' in m else 'new') for m in steps[-1]['moved']],'transient',list(steps[-1]['transient'].keys()),flush=True)
    async def tap(sel):
      xy=await center(pg,sel)
      if not xy: return False
      await pg.touchscreen.tap(*xy); return True
    async def taptxt(t):
      xy=await pg.evaluate(VISTXT,t)
      if not xy: return False
      await pg.wait_for_timeout(200); await pg.touchscreen.tap(*xy); return True
    async def geo(t):
      await tap('#bGeo'); await pg.wait_for_timeout(1200)
      if await taptxt(t): return True
      R.setdefault('geo_items',{})[t]=await pg.evaluate("()=>[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent).slice(0,15).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40))")
      await tap('#bGeo'); return False
    async def seq(*fs):
      r=True
      for f in fs: r=(await f()) and r; await pg.wait_for_timeout(900)
      return r
    async def tick(i):
      return await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
    async def taptick(i):
      xy=await tick(i); await pg.touchscreen.tap(*xy); return True
    async def lyr(k):
      return await seq(lambda: tap('#bLyr'), lambda: tap(f'#lyrRow button[data-k={k}]'))
    async def back():
      for s in ['#listView .lvback','#listView [aria-label*=ack i]','.backbtn','#bBack']:
        if await center(pg,s): await tap(s); return s
      xy=await pg.evaluate("()=>{const e=[...document.querySelectorAll('#listView button, #listView .lvb, #listView [role=button]')].find(e=>e.offsetParent&&/^[<‹]?$/.test(e.innerText.trim())&&e.getBoundingClientRect().width<60);if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,e.className]}")
      if xy: await pg.touchscreen.tap(xy[0],xy[1]); return 'found:'+str(xy[2])
      return False
    await c.close(); c,pg,log2=await ctx(b,W,H,W<600,eng); log['pageerr']+=log2['pageerr']
    await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__ysl",timeout=60000); await pg.wait_for_timeout(5000)
    await step('open-time-slider-US',lambda: tap('#bTime'))
    await step('geo-menu-all-states',lambda: geo('All States'),5000)
    await step('list-drill-MA',lambda: taptxt('MA'),5000)
    await step('list-year-2020-MA',lambda: taptick(1),3000)
    await step('list-year-2024-MA',lambda: taptick(2),3000)
    await step('list-drill-Worcester',lambda: taptxt('Worcester'),5000)
    await step('list-ushouse-Worcester',lambda: lyr('ushouse'),5000)
    await step('list-ushouse-off',lambda: lyr('ushouse'),5000)
    await step('list-back-1',back,4000)
    await step('list-back-2',back,4000)
    await step('chart-gbar',lambda: seq(lambda: tap('#chartBox .cmain'), lambda: tap('#chartBox .copts button[data-ch=gbar]') ),3000)
    await step('list-drill-MA-gbar',lambda: taptxt('MA'),5000)
    await step('list-drill-Worcester-gbar',lambda: taptxt('Worcester'),5000)
    await step('list-back-gbar-1',back,4000)
    await step('list-back-gbar-2',back,4000)
    await step('view-map-US',lambda: tap('#bGlobe'),3500)
    R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:8]; R['reqfail']=log['reqfail'][:10]; R['http']=log['http'][:10]
    await c.close(); await b.close()
  json.dump(R,open(f'b1622h0200-layout3-{eng}-{size}{sys.argv[3] if len(sys.argv)>3 else ""}.json','w'),indent=1)
asyncio.run(main())
