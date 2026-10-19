# pass 27: QA-020 precise: Back LA cities -> CA counties: touch/click event times, first #listView DOM change and the paint after it,
# first frame where the CA counties rows are on screen, longest frame gap, heat count per frame (absolute performance.now()).
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
import os; URL=os.environ.get("URL",URL)
EV="""()=>{const E=window.__ev={};['touchstart','touchend','pointerup','click'].forEach(t=>document.addEventListener(t,e=>{if(!(t in E))E[t]=e.timeStamp},{capture:true}));
 const lv=document.getElementById('listView');const mo=new MutationObserver(()=>{if(E.mut)return;E.mut=performance.now();requestAnimationFrame(()=>setTimeout(()=>{E.mutpaint=performance.now()},0));mo.disconnect()});mo.observe(lv,{childList:true,subtree:true,characterData:true});
 const F=window.__fr=[];const HN=()=>{try{const f=l=>l.getLayers?l.getLayers().reduce((a,x)=>a+f(x),0):1;return heatLayer?f(heatLayer):-1}catch(e){return -2}};
 const t0=performance.now();const f=()=>{setTimeout(()=>{const t=performance.now();const rows=[...document.querySelectorAll('#listView .lvrow')];const fv=rows.find(r=>r.offsetParent);F.push([Math.round(t),rows.length,fv?((fv.querySelector('.nmx')||fv).textContent||'').trim().slice(0,20):'',HN(),(document.getElementById('crumbs')||{}).innerText||'']);if(t-t0<2500)requestAnimationFrame(f)},0)};requestAnimationFrame(f)}"""
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def meas(pg,xy,want_first,want_n):
  await pg.evaluate(EV); await pg.wait_for_timeout(120); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(2700)
  E=await pg.evaluate("()=>window.__ev"); F=await pg.evaluate("()=>window.__fr")
  t0=E.get('touchstart') or E.get('pointerup')
  rel=lambda v: None if v is None else round(v-t0)
  ok=[f for f in F if f[0]>=t0 and f[2].startswith(want_first) and (want_n is None or f[1]==want_n)]
  fr=[f for f in F if f[0]>=t0]; g=[fr[i+1][0]-fr[i][0] for i in range(len(fr)-1)]
  first_after=fr[0] if fr else None
  hs=[]; prev=None
  for f in fr:
    k=(f[1],f[2],f[3])
    if k!=prev: hs.append([round(f[0]-t0)]+f[1:4]); prev=k
  return {'touchend':rel(E.get('touchend')),'click':rel(E.get('click')),'first_frame':rel(first_after[0]) if first_after else None,
          'first_dom_change':rel(E.get('mut')),'paint_after_dom_change':rel(E.get('mutpaint')),'rows_visible':rel(ok[0][0]) if ok else None,
          'max_gap':max(g) if g else None,'timeline':hs}
MC="""()=>{const m=window.__map;const c=m.getCenter();const f=l=>l&&l.getLayers?l.getLayers().reduce((a,x)=>a+f(x),0):(l?1:0);let fo=-9,hn=-9;try{fo=(typeof focusLayer!=='undefined'&&focusLayer)?(m.hasLayer(focusLayer)?f(focusLayer):-1):0}catch(e){}try{hn=heatLayer?(m.hasLayer(heatLayer)?f(heatLayer):-1):0}catch(e){}
 return {ll:[+c.lat.toFixed(3),+c.lng.toFixed(3),m.getZoom()],focus:fo,heat:hn,crumbs:(document.getElementById('crumbs')||{}).innerText,vis:!!(m.getContainer().offsetParent)}}"""
async def tomap(pg,tag,shot):
  await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); out=[]; t=0
  for w in [80,300,700,1200,2500,4000]:
    await pg.wait_for_timeout(w-t); t=w; out.append([w,await pg.evaluate(MC)])
  await pg.screenshot(path=shot); return out
async def main():
  eng=sys.argv[1]; sizes=sys.argv[2].split(','); reps=int(sys.argv[3]) if len(sys.argv)>3 else 2
  SZ={'1024x768':(1024,768),'1024x576':(1024,576),'390':(390,844),'375':(375,667),'320':(320,568)}; R={'eng':eng,'sizes':{}}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for size in sizes:
      W,H=SZ[size]; c,pg,log=await ctx(b,W,H,W<600,eng); S=R['sizes'][size]={'reps':[]}
      try:
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000); S['build']=R['build']=await pg.evaluate("window.BUILD")
        await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
        await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        for rep in range(reps):
          r={}
          r['drillCA']=await meas(pg,await pg.evaluate(NMXY,'CA'),'Los Angeles',58); await pg.wait_for_timeout(2500)
          r['drillLA']=await meas(pg,await pg.evaluate(NMXY,'Los Angeles'),'Los Angeles city',None); await pg.wait_for_timeout(3000)
          r['back']=await meas(pg,await center(pg,'#bBack'),'Los Angeles',58); await pg.wait_for_timeout(2500)
          r['back2']=await meas(pg,await center(pg,'#bBack'),'CA',None); await pg.wait_for_timeout(2500)
          S['reps'].append(r)
          print(eng,size,S['build'],rep,json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='timeline'} for k,v in r.items()}),flush=True)
          print('   back timeline',r['back']['timeline'][:6],flush=True)
        try:
          sh=f"../shots/b{S['build'][-4:]}p31-{eng[:2]}-{size}-back2-"
          S['map_check']={'allstates_hidden':await pg.evaluate(MC)}
          S['map_check']['allstates_to_map']=await tomap(pg,'us',sh+'us-map.png')
          await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
          xy=await pg.evaluate(NMXY,'CA'); S['map_check']['ca_xy']=xy; S['map_check']['crumbs_list']=await pg.evaluate("()=>[document.getElementById('crumbs').innerText,document.getElementById('listView').offsetParent?1:0]")
          await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(250)
          S['map_check']['CA_quick_to_map']=await tomap(pg,'ca',sh+'CA-map-quick.png')
          await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Los Angeles'))); await pg.wait_for_timeout(3000)
          await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(2500)
          await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(2500)
          S['map_check']['back_back_to_map']=await tomap(pg,'us2',sh+'us-map-after-backs.png')
          print('  map_check',json.dumps(S['map_check'])[:3000],flush=True)
        except Exception as e: S['map_check_EXC']=str(e)[:300]; print('EXC map',e,flush=True)
      except Exception as e: S['EXC']=str(e)[:300]; print('EXC',size,str(e)[:200],flush=True)
      S['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:8]+log['reqfail'][:5]+log['http'][:5]
      await c.close()
    await b.close()
  json.dump(R,open(f"b{R.get('build','0000')[-4:]}p31-back2-{eng}.json",'w'),indent=1)
asyncio.run(main())
