# pass 14 (build 1582): candidate icons keep the map view's spot in list/pie/bar/line; no text/tooltip; single-year bar visible, clear of the rail
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
Q="""()=>{ const vis=e=>{ const r=e.getBoundingClientRect(); if(!(r.width>0)) return false; let x=e; while(x&&x!==document.body){ const s=getComputedStyle(x); if(s.visibility==='hidden'||s.display==='none'||+s.opacity===0) return false; x=x.parentElement; } return true; };
 const ims=[...document.querySelectorAll('#cands img')].filter(vis).map(i=>{const r=i.getBoundingClientRect(); return [Math.round(r.left*2)/2,Math.round(r.top*2)/2,Math.round(r.width),Math.round(r.height)]}).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
 const txt=[...document.querySelectorAll('#cands .cand .cpt,#cands .cand .cn,#cands .cand .cs,#cands .cand .cw')].filter(vis).map(e=>e.textContent.slice(0,20));
 // any visible text node within 40px right of / overlapping an icon
 const near=[]; const imr=[...document.querySelectorAll('#cands img')].filter(vis).map(i=>i.getBoundingClientRect());
 const w=document.createTreeWalker(document.getElementById('cands')||document.body,NodeFilter.SHOW_TEXT); let n; while(n=w.nextNode()){ const s=n.textContent.trim(); if(!s||!n.parentElement||!vis(n.parentElement)) continue; const rg=document.createRange(); rg.selectNodeContents(n); const r=rg.getBoundingClientRect(); if(!r.width) continue; for(const q of imr){ if(r.left<q.right+40&&r.right>q.left-4&&r.top<q.bottom&&r.bottom>q.top){ near.push(s.slice(0,24)); break; } } }
 const rl=document.querySelector('.rail'), rr=rl&&rl.getBoundingClientRect();
 const sb=document.querySelector('.sebar'); let se=null; if(sb&&vis(sb)){ const r=sb.getBoundingClientRect(); const bars=[...sb.querySelectorAll('.sebt i,.sebt b')].map(e=>e.getBoundingClientRect().right); se={top:Math.round(r.top),bottom:Math.round(r.bottom),left:Math.round(r.left),right:Math.round(r.right),maxBarRight:Math.round(Math.max(...bars,0)),rows:sb.querySelectorAll('.sebr').length,labels:[...sb.querySelectorAll('.sebr')].map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40))}; }
 return {ims,txt,near,chartMode:window.chartMode,chv:document.body.classList.contains('chv'),list:document.body.classList.contains('listmode'),rail:rr&&rr.width?[Math.round(rr.left),Math.round(rr.top),Math.round(rr.width),Math.round(rr.height)]:null,sebar:se,vh:innerHeight,vw:innerWidth,crumbs:(document.getElementById('crumbs')||{}).innerText}; }"""
FR="""(ms)=>new Promise(res=>{const fr=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const a=[...document.querySelectorAll('#cands img')].filter(i=>{const r=i.getBoundingClientRect();if(!r.width)return false;let x=i;while(x&&x!==document.body){const s=getComputedStyle(x);if(s.visibility==='hidden'||s.display==='none'||+s.opacity===0)return false;x=x.parentElement}return true}).map(i=>{const r=i.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.width)]}).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);const k=JSON.stringify(a);if(!fr.length||fr[fr.length-1][1]!==k)fr.push([Math.round(t),k]);if(t<ms)requestAnimationFrame(f);else res(fr)};requestAnimationFrame(f)})"""
async def main():
  eng=sys.argv[1]; size=sys.argv[2]; W,H={'1024x768':(1024,768),'1024x576':(1024,576),'390':(390,844),'375':(375,667),'320':(320,568)}[size]
  R={'eng':eng,'size':size,'views':{},'frames':{},'tips':{}}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__ysl",timeout=60000); await pg.wait_for_timeout(4000)
    R['build']=await pg.evaluate("window.BUILD")
    async def tap(sel):
      xy=await center(pg,sel)
      if not xy: return False
      await pg.touchscreen.tap(*xy); return True
    async def rec(name,action,settle=2500):
      fr=asyncio.ensure_future(pg.evaluate(FR,settle)); ok=await action(); frames=await fr; await pg.wait_for_timeout(300)
      q=await pg.evaluate(Q); R['views'][name]=q; R['frames'][name]=frames; await safeshot(pg,f"../shots/b1584p16-{eng[:2]}-{size}-icons-{name}.png")
      print(name,ok,q['chartMode'],'chv',q['chv'],'ims',q['ims'],'txt',q['txt'],'near',q['near'],'sebar',q['sebar'],'frames',len(frames),flush=True)
    async def chart(k):
      if not await tap('#chartBox .cmain'):
        await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()")
      await pg.wait_for_timeout(700)
      if not await tap(f'#chartBox .copts button[data-ch={k}]'):
        await pg.evaluate(f"()=>{{const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch==='{k}'); b&&b.click()}}")
      return True
    async def tip(name):
      r=await pg.evaluate("()=>{const i=[...document.querySelectorAll('#cands img')].find(i=>i.getBoundingClientRect().width>0); if(!i) return null; const q=i.getBoundingClientRect(); return [q.left+q.width/2,q.top+q.height/2]}")
      if not r: R['tips'][name]=None; return
      await pg.touchscreen.tap(r[0],r[1]); await pg.wait_for_timeout(600)
      t=await pg.evaluate("()=>{const b=document.getElementById('partyBub'); const tt=[...document.querySelectorAll('[role=tooltip],.tip,.tooltip,#partyBub')].filter(e=>e.getBoundingClientRect().width>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden').map(e=>e.textContent.slice(0,60)); return tt}")
      R['tips'][name]=t; print('tip',name,t,flush=True)
      await pg.wait_for_timeout(300)
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000)
    await rec('map24',lambda: asyncio.sleep(0))
    await rec('list24',lambda: tap('#bGlobe'))
    await rec('pie24',lambda: chart('pie')); await tip('pie24')
    await rec('bar24',lambda: chart('bar')); await tip('bar24')
    await rec('pie24b',lambda: chart('pie'))
    await rec('map24b',lambda: tap('#bGlobe'))
    # range '20>'24
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); }"); await pg.wait_for_timeout(1200)
    await rec('map2024r',lambda: pg.evaluate("()=>{window.__ySelectAll();return true}"))
    await rec('list2024r',lambda: tap('#bGlobe'))
    await rec('rbar',lambda: chart('bar')); await tip('rbar')
    await rec('rline',lambda: chart('line')); await tip('rline')
    await rec('rbar2',lambda: chart('bar'))
    await rec('map2024r2',lambda: tap('#bGlobe'))
    await rec('map1624r',lambda: pg.evaluate("()=>{window.__ySet16(2);return true}"),4000)
    await rec('list1624r',lambda: tap('#bGlobe'))
    await rec('r16line',lambda: chart('line'))
    await rec('r16bar',lambda: chart('bar'))
    await rec('map1624r2',lambda: tap('#bGlobe'))
    # single 2016
    await rec('map2016',lambda: pg.evaluate("()=>{const w=document.querySelector('.kn.a');return true}"),300)
    R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:8]
    await c.close(); await b.close()
  json.dump(R,open(f'b1584p16-icons-{eng}-{size}.json','w'),indent=1)
asyncio.run(main())
