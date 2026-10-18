import asyncio,sys,json,statistics as S
from playwright.async_api import async_playwright
from common import *
# one slider change: dispatch input+change, then per frame watch list text and map fill colours; returns ms to list change and to map change
CH="""async(v)=>{const lv=document.getElementById('listView');const rows=()=>[...lv.querySelectorAll('.lvrow.la')].filter(r=>r.offsetParent).slice(0,12).map(r=>r.innerText).join('#');
 const fills=()=>{let s='';let n=0;for(const k in map._layers){const l=map._layers[k];if(l.options&&l.options.fillColor&&n<400){s+=l.options.fillColor;n++}}return s};
 const r0=rows(),f0=fills();const s=document.getElementById('yslider');const t0=performance.now();
 s.value=v;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}));
 const tsync=performance.now()-t0;let tl=null,tm=null;
 await new Promise(res=>{const loop=()=>{const t=performance.now()-t0;if(tl===null&&rows()!==r0)tl=t;if(tm===null&&fills()!==f0)tm=t;if((tl!==null&&tm!==null)||t>1500)res();else requestAnimationFrame(loop)};requestAnimationFrame(loop)});
 return {sync:Math.round(tsync),list:tl&&Math.round(tl),map:tm&&Math.round(tm),ym:window.__ymode()}}"""
CONS="""()=>{const ym=window.__ymode();const rows=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '));
 const lab=[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label'));return {ym,slider:document.getElementById('yslider').value,rows,cands:lab}}"""
async def setup(pg,level):
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  if level=='ushouse':
    await pg.evaluate("()=>[...document.querySelectorAll('li')].find(e=>e.offsetParent&&e.innerText.trim()==='US House districts').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
  else:
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
    await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()==='PA'});r.querySelector('.nmx').click()}"); await pg.wait_for_timeout(6000)
  await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1500)
async def main():
  eng=sys.argv[1]; out={}
  global LEVELS,NCH; NCH=12; LEVELS=sys.argv[2].split(',')
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    SZ=sys.argv[4].split(',') if len(sys.argv)>4 else None
    for tag,W,H,mob in VPS:
      if SZ and tag not in SZ: continue
      for level in LEVELS:
        c,pg,log=await ctx(b,W,H,mob,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000)
        await setup(pg,level); R={'build':await pg.evaluate("()=>window.BUILD"),'lv':await pg.evaluate("()=>window.__laInfo().lv+' n='+document.querySelectorAll('#listView .lvrow.la').length")}
        THR=len(sys.argv)>3 and sys.argv[3]=='throttle'
        if THR:
          cdp=await c.new_cdp_session(pg); await cdp.send('Emulation.setCPUThrottlingRate',{'rate':4}); await pg.wait_for_timeout(1500); R['cpu']='4x'
        await pg.evaluate("()=>{window.__cls=0;window.__shifts=[]}")
        mx=await pg.evaluate("()=>document.getElementById('yslider').max")
        res=[]
        for i in range(NCH):
          v='0' if i%2==0 else mx
          r=await pg.evaluate(CH,v); res.append(r); await pg.wait_for_timeout(700)
        L=[r['list'] for r in res if r['list'] is not None]; M=[r['map'] for r in res if r['map'] is not None]
        R['list_ms']={'median':S.median(L) if L else None,'max':max(L) if L else None,'n':len(L),'missed':NCH-len(L)}
        R['map_ms']={'median':S.median(M) if M else None,'max':max(M) if M else None,'n':len(M),'missed':NCH-len(M)}
        R['sync_ms']=[r['sync'] for r in res]; R['ym']=[r['ym'] for r in res]
        R['cls_slow']=await pg.evaluate("()=>[window.__cls,window.__shifts.slice(0,5)]")
        await pg.screenshot(path=f"../shots/b1568-{eng[:2]}{"-4x" if len(sys.argv)>3 and sys.argv[3]=="throttle" else ""}-{tag.replace('iphone','').replace('ipad','')}-{level}-slider.png")
        # fast repeated drags: 15 changes 25 ms apart, ending at 2020 (value 0)
        await pg.evaluate("()=>{window.__cls=0;window.__shifts=[]}")
        await pg.evaluate("async(mx)=>{const s=document.getElementById('yslider');const seq=[];for(let i=0;i<15;i++)seq.push(i%3==0?mx:(i%3==1?'1':'0'));seq.push('0');for(const v of seq){s.value=v;s.dispatchEvent(new Event('input',{bubbles:true}));await new Promise(r=>setTimeout(r,25))}s.dispatchEvent(new Event('change',{bubbles:true}))}",mx)
        await pg.wait_for_timeout(2500)
        R['after_fast']=await pg.evaluate(CONS); R['cls_fast']=await pg.evaluate("()=>[window.__cls,window.__shifts.slice(0,5)]")
        # map popup at screen centre (map mode) to compare year: switch to map via globe, tap centre
        await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2000)
        await pg.touchscreen.tap(W//2,H//2); await pg.wait_for_timeout(1500)
        R['popup_after_fast']=await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.replace(/\\n/g,' | ').slice(0,200))")
        await pg.screenshot(path=f"../shots/b1568-{eng[:2]}{"-4x" if len(sys.argv)>3 and sys.argv[3]=="throttle" else ""}-{tag.replace('iphone','').replace('ipad','')}-{level}-fastdrag-map.png")
        R['err']=log['pageerr']+log['console']; out[tag+' '+level]=R; await c.close(); print(tag,level,json.dumps(R)[:900],flush=True)
    await b.close()
  json.dump(out,open(f'slider-{eng}-{sys.argv[2]}-'+'_'.join(sys.argv[3:])+'.json','w'),indent=1)
asyncio.run(main())
