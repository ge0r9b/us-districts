# t240/t249: list-all rows follow the chart-type setting (bar / line / pie); line labels sit under their line between the points; single-county delta line chart too
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
SETCH="""m=>{ const open=document.querySelector('[aria-label=Chart]'); const cur=window.chartMode; if(cur===m) return; open.click(); }"""
async def setchart(pg,m):
  cur=await pg.evaluate("()=>window.chartMode")
  if cur==m: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("m=>{ const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch===m); if(b) b.click(); }",m); await pg.wait_for_timeout(2500)
LST="""()=>{ const lv=document.getElementById('listView'); let L=1e9; document.querySelectorAll('.rail .rbtn,#bGeo,#bGlobe,#bNum,#bLyr,#bTime,#bSearch,#bChart,.xrow .lbtn').forEach(b=>{const r=b.getBoundingClientRect(); if(r.width>0&&getComputedStyle(b).display!=='none'&&r.left>innerWidth*.5&&r.left<L) L=r.left});
 const rows=[...lv.querySelectorAll('.lvrow.la')].filter(r=>r.offsetParent); const R=r=>{const b=r.getBoundingClientRect(); return [b.left,b.top,b.right,b.bottom]};
 const lines=rows.filter(r=>r.querySelector('.lnw')).map(r=>{ const w=r.querySelector('.lnw'), th=[...w.querySelectorAll('.lth')].map(R), lb=[...w.querySelectorAll('.llb')].map(x=>({r:R(x),t:x.textContent,cls:x.className})), sv=w.querySelector('svg').getBoundingClientRect(), pl=[...w.querySelectorAll('polyline')].map(p=>p.getAttribute('points')); return {w:R(w),th,lb,sv:[sv.left,sv.top,sv.width,sv.height],pl} });
 return {L,n:rows.length,bars:rows.filter(r=>r.querySelector('.sbw:not(.nd)')).length,lnw:lines.length,pwr:rows.filter(r=>r.querySelector('.pwr')).length,circles:rows.filter(r=>r.querySelector('.pwr')).map(r=>r.querySelectorAll('.pwr circle').length).slice(0,3),pth:rows.filter(r=>r.querySelector('.pwr')).map(r=>r.querySelectorAll('.pth').length).slice(0,3),lines:lines.slice(0,12),over:rows.filter(r=>{const w=r.querySelector('.lnw,.pwr'); return w&&w.getBoundingClientRect().right>L}).length}}"""
def inter(a,b): return not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])
async def run(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=1; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(2500)
  for mode in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1500)
    await setchart(pg,"bar"); s=await pg.evaluate(LST); ck(tag+" %s bar: rows are bars"%mode,s['bars']>=40 and s['lnw']==0 and s['pwr']==0,s)
    await setchart(pg,"line"); s=await pg.evaluate(LST)
    ck(tag+" %s line: every row is a two-point line graph (no bars)"%mode,s['lnw']>=40 and s['bars']==0,{k:s[k] for k in ('n','bars','lnw')})
    ck(tag+" %s line: 4 endpoint thumbnails per row; graph ends left of the button column"%mode,all(len(x['th'])==4 for x in s['lines']) and s['over']==0,(s['over'],[len(x['th']) for x in s['lines'][:3]]))
    g=await pg.evaluate("()=>{ const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.querySelector('.lnw')).slice(0,20); const bar=22; return {h:Math.min(...r.map(x=>x.getBoundingClientRect().height)),sw:Math.min(...r.map(x=>parseFloat(getComputedStyle(x.querySelector('polyline')).strokeWidth))),th:Math.min(...r.map(x=>x.querySelector('.lth').getBoundingClientRect().width))} }")
    ck(tag+" %s line: rows at least as tall as bar rows (>=44px), lines 3-4px+, thumbnails >=20px"%mode,g['h']>=44 and g['sw']>=3 and g['th']>=20,g)
    ok1=ok2=ok3=True; bad=None
    for x in s['lines']:
      th=x['th']; xl=max(t[2] for t in th[:2]); xr=min(t[0] for t in th[2:]); sv=x['sv']
      for lb in x['lb']:
        cx=(lb['r'][0]+lb['r'][2])/2
        if not (xl-1<=cx<=xr+1): ok1=False; bad=(cx,xl,xr)
        if any(inter(lb['r'],t) for t in th): ok2=False; bad=('thumb',lb)
        if lb['r'][2]>s['L']: ok3=False
    ck(tag+" %s line: value labels centred between the two points"%mode,ok1,bad); ck(tag+" %s line: labels never overlap thumbnails"%mode,ok2,bad); ck(tag+" %s line: labels not under the floating buttons"%mode,ok3)
    x=s['lines'][0]; ck(tag+" %s line: label y just under (or beside, if lines crowd) its line"%mode,all(-14<=lb['r'][1]-(x['sv'][1])<=x['sv'][3]+14 for lb in x['lb']),x)
    s0=await pg.evaluate("()=>[...document.querySelectorAll('[aria-label=Chart]')].length"); 
    await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(400)
    o=await pg.evaluate("()=>[...document.querySelectorAll('.copts button')].map(b=>b.dataset.ch)"); await pg.evaluate("()=>document.getElementById('chartDim').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true}))"); await pg.wait_for_timeout(400)
    ck(tag+" %s range: chart menu has no pie"%mode,"pie" not in o,o)
    await setchart(pg,"line"); 
    if mode=="pct": await pg.screenshot(path="/tmp/cm-%s-line.png"%tag)
  # single point: bar + pie rows
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=2; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(2500)
  s=await pg.evaluate(LST); ck(tag+" single point: line auto-switched to bar rows",s['lnw']==0 and s['bars']>=40,{k:s[k] for k in ('n','bars','lnw')})
  await setchart(pg,"pie"); s=await pg.evaluate(LST); ck(tag+" single point pie: one disc per row (3 arcs) + 2 legend thumbnails, no bars",s['pwr']>=40 and s['bars']==0 and all(c==3 for c in s['circles']) and all(p==2 for p in s['pth']),s)
  ck(tag+" single point pie: stays left of the button column",s['over']==0,s['over'])
  await pg.screenshot(path="/tmp/cm-%s-pie.png"%tag)
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=1; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(2500)
  s=await pg.evaluate(LST); ck(tag+" pie + range: rows fall back to bars",s['pwr']==0 and s['bars']>=40,{k:s[k] for k in ('n','bars','pwr')})
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=2; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(2500)
  s=await pg.evaluate(LST); ck(tag+" back to single point: pie rows restored",s['pwr']>=40,{k:s[k] for k in ('n','bars','pwr')})
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=1; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(1500); await setchart(pg,"bar")
  s=await pg.evaluate(LST); ck(tag+" back to bar: rows are bars again",s['bars']>=40 and s['lnw']==0,s)
  # Alabama counties list-all, line
  await pg.evaluate("()=>{ state.value='Alabama'; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(2500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5500)
  await setchart(pg,"line"); s=await pg.evaluate(LST); ck(tag+" Alabama counties list-all: line rows",s['lnw']>=60 and s['bars']==0,{k:s[k] for k in ('n','bars','lnw')})
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def single(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>{ state.value='Alabama'; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(3000)
  await pg.evaluate("()=>{ county.value='Autauga County'; county.onchange&&county.onchange(); }"); await pg.wait_for_timeout(3500)
  await pg.wait_for_timeout(1000)
  if not await pg.evaluate("()=>document.body.classList.contains('listmode')"): await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1000)
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=1; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(2000)
  for mode in ("num","pct"):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1000); await setchart(pg,"line"); await pg.wait_for_timeout(1500)
    r=await pg.evaluate("""()=>{ const ch=document.querySelector('.dlch'); if(!ch) return null; const svg=ch.querySelector('svg'); const sr=svg.getBoundingClientRect(); const R=e=>{const b=e.getBoundingClientRect(); return [b.left,b.top,b.right,b.bottom]}; const g=[...svg.querySelectorAll('g')]; const out=g.map(gg=>{ const ln=gg.querySelectorAll('line')[1], t=gg.querySelector('text.dlv'); if(!ln||!t) return null; const x1=+ln.getAttribute('x1'),x2=+ln.getAttribute('x2'),y1=+ln.getAttribute('y1'),y2=+ln.getAttribute('y2'); return {tx:+t.getAttribute('x'),ty:+t.getAttribute('y'),x1,x2,y1,y2,tr:R(t),txt:t.textContent} }).filter(Boolean); const th=[...ch.querySelectorAll('img.dmt')].map(R); let L=1e9; document.querySelectorAll('.rail .rbtn,#bGeo,#bGlobe,#bNum,#bTime,#bSearch').forEach(b=>{const r=b.getBoundingClientRect(); if(r.width>0&&getComputedStyle(b).display!=='none'&&r.left>innerWidth*.5&&r.left<L) L=r.left}); return {out,th,L} }""")
    ck(tag+" single-county delta line (%s): chart present with 2 labelled lines"%mode,bool(r) and len(r['out'])==2,r)
    if not r or len(r['out'])!=2: continue
    ok=all(abs(o['tx']-(o['x1']+o['x2'])/2)<1 for o in r['out']); ck(tag+" single-county (%s): label x centred between the two points"%mode,ok,r['out'])
    ck(tag+" single-county (%s): label y just under the line (0-34px below its midpoint)"%mode,all(0<=o['ty']-(o['y1']+o['y2'])/2<=34 for o in r['out']),r['out'])
    ck(tag+" single-county (%s): labels clear of the thumbnails and the button column"%mode,all(not inter(o['tr'],t) for o in r['out'] for t in r['th']) and all(o['tr'][2]<=r['L'] for o in r['out']),r)
    await pg.screenshot(path="/tmp/cm-%s-single-%s.png"%(tag,mode))
  ck(tag+" single no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"phone",{"width":390,"height":780},True); await single(b,"phone",{"width":390,"height":780},True)
    await run(b,"desktop",{"width":1280,"height":800},False); await single(b,"desktop",{"width":1280,"height":800},False)
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
