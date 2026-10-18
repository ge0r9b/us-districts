# t272-t275: delta lists sort by |net change| as displayed (all levels, % and #); single-year # bars are proportional to total votes on one common scale; Arizona 2020 precincts present
import asyncio,sys,re
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
def mag(t):
  m=re.search(r'([\d.,]+)\s*([KM]?)',t.replace('\u2212','-')); 
  if not m: return None
  v=float(m.group(1).replace(',','')); return v*(1e3 if m.group(2)=='K' else 1e6 if m.group(2)=='M' else 1)
NETS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>{const n=r.querySelector('.net'); return n?n.textContent:null}).filter(Boolean)"
async def slide(pg,v):
  await pg.evaluate("v=>{ const s=document.getElementById('yslider'); s.value=v; s.dispatchEvent(new Event('input',{bubbles:true})); }",v); await pg.wait_for_timeout(2500)
async def enter(pg):
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5500)
async def run(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await enter(pg)
  # single-year # mode: proportional bars
  await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(2000)
  r=await pg.evaluate("""()=>{ let L=1e9; document.querySelectorAll('#bGeo,#bGlobe,#bNum,#bTime,#bSearch,#bChart,.rail .rbtn').forEach(b=>{const q=b.getBoundingClientRect(); if(q.width>0&&getComputedStyle(b).display!=='none'&&q.left>innerWidth*.5&&q.left<L) L=q.left});
    const tot=new Map(__LA.order.map(o=>[o[0],o[1]])); const rows=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent&&r.querySelector('.sbw.ab')).map(r=>{ const b=r.querySelector('.sbw.ab').getBoundingClientRect(); const nm=r.querySelector('b.rn'); const sg=r.querySelector('.sbw.ab .sg.rep'); return {w:b.width,rp:sg?sg.getBoundingClientRect().width:0,right:b.right,t:null,nm:(nm.title||nm.textContent)} });
    return {L,rows:rows.slice(0,60),order:__LA.order.slice(0,60)} }""")
  ab=r['rows']; ck(tag+" # mode single year: rows are scaled bars",len(ab)>=30,len(ab))
  if ab:
    mx=max(x['w'] for x in ab); ck(tag+" ...largest bar capped left of the button column",all(x['right']<=r['L']+1 for x in ab),(mx,r['L']))
    # build 1551: order values = votes of the top-ranked selected answer (Trump) sorted desc; bar length = row total on one scale, so the Trump segment (px) must be non-increasing and proportional to the order values
    ws=[x['rp'] for x in ab]; ck(tag+" ...Trump segment lengths follow the sort key (non-increasing in the by-Trump-votes sort)",all(ws[i]>=ws[i+1]-1 for i in range(len(ws)-1)),ws[:12])
    tt=[o[1] for o in r['order'] if o[1]]; k=min(len(ws),len(tt)); i=k//2; ratio_w=ws[0]/max(ws[i],1); ratio_t=tt[0]/tt[i]
    ck(tag+" ...segment widths proportional to the key votes (first vs middle row)",abs(ratio_w-ratio_t)/ratio_t<0.12 or ws[i]<=26,(ratio_w,ratio_t))
  await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500)
  r=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la .sbw')].filter(e=>e.offsetParent&&!e.classList.contains('nd')).slice(0,20).map(e=>Math.round(e.getBoundingClientRect().width))")
  ck(tag+" % mode single year: full-width shares unchanged (equal widths)",len(set(r))<=2,r)
  # delta sort, states
  await slide(pg,1)
  for m in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",m); await pg.wait_for_timeout(2500)
    n=await pg.evaluate(NETS); v=[mag(x) for x in n if mag(x) is not None]
    ck(tag+" delta %s states: net magnitudes non-increasing (%d rows)"%(m,len(v)),len(v)>=40 and all(v[i]>=v[i+1]-1e-9 for i in range(len(v)-1)),n[:12])
  # Arizona counties
  await pg.evaluate("()=>{ state.value='Arizona'; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(3000)
  await enter(pg)
  for m in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",m); await pg.wait_for_timeout(2500)
    n=await pg.evaluate(NETS); v=[mag(x) for x in n if mag(x) is not None]
    ck(tag+" delta %s Arizona counties: non-increasing (%d rows)"%(m,len(v)),len(v)>=10 and all(v[i]>=v[i+1]-1e-9 for i in range(len(v)-1)),n[:12])
  # flip reverses
  await pg.evaluate("()=>document.getElementById('laSort').click()"); await pg.wait_for_timeout(1500)
  n=await pg.evaluate(NETS); v=[mag(x) for x in n if mag(x) is not None]; ck(tag+" flip reverses (non-decreasing)",all(v[i]<=v[i+1]+1e-9 for i in range(len(v)-1)),n[:8])
  # Arizona 2020 precinct data present
  k=await pg.evaluate("()=>{ const P=(window.PREC20||{})['Arizona']||[]; const c={}; P.forEach(r=>c[r[0]]=1); return [P.length,Object.keys(c).length] }")
  ck(tag+" Arizona 2020 precincts loaded (1,400+ rows, all 15 counties)",k[0]>1400 and k[1]==15,k)
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,"phone",{"width":390,"height":780},True); await run(b,"desktop",{"width":1280,"height":800},False); await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
