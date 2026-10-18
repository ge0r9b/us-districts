# usage: python3 tests/single-entity-chart.py URL -- build 1556: a single entity (Alabama) shows ONE big chart and no bar option:
# one year -> big pie centred between the text indent (x=52) and the right edge, clear of the thumbnails and floating buttons;
# two years -> line chart whose vertical axis has 3-5 light hairlines with small mid-gray labels (% in % mode, abbreviated votes in # mode)
# and whose points sit on the time slider's '20 / '24 positions; the plural row ('Alabama counties') brings the bar list back.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:700]); fails+=0 if ok else 1
R="""()=>{const R=e=>{if(!e) return null; const r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom]};
 const vis=e=>e.offsetParent&&getComputedStyle(e).visibility!=='hidden'&&e.getBoundingClientRect().width>0;
 return {mode:window.chartMode, vw:innerWidth, pie:R(document.querySelector('.cpanel .cpie1 svg, .cpanel .cpieL svg')), ax:[...document.querySelectorAll('.dlx .dlat')].map(t=>[t.textContent,R(t),getComputedStyle(t).fill]), grid:[...document.querySelectorAll('.dlx .dlax line')].map(l=>[l.getAttribute('stroke'),R(l)]),
   dots:[...document.querySelectorAll('.dlx circle')].map(R), ticks:[...document.querySelectorAll('#ysl .tk i')].map(d=>{const r=d.getBoundingClientRect(); return r.left+r.width/2}),
   imgs:[...document.querySelectorAll('.dlx img, .cands img')].filter(vis).map(R), btns:[...document.querySelectorAll('button.rbtn')].filter(vis).map(R), rows:document.querySelectorAll('#listView .lvrow.la').length, la:window.__laInfo().on}}"""
OPTS="()=>{const c=document.querySelector('button.rbtn.cmain'); c.click(); return new Promise(r=>setTimeout(()=>{const o=[c.dataset.ch,...[...document.querySelectorAll('.copts button')].map(b=>b.dataset.ch)]; document.getElementById('chartDim').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); r(o)},600))}"
def ov(a,b,m=0): return a[0]<b[2]-m and b[0]<a[2]-m and a[1]<b[3]-m and b[1]<a[3]-m
async def pick(pg,m):
  await pg.evaluate("(m)=>{ if(window.chartMode===m) return; const c=document.querySelector('button.rbtn.cmain'); c.click(); setTimeout(()=>{const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch===m); if(b) b.click(); else if(c.dataset.ch===m) c.click();},500)}",m); await pg.wait_for_timeout(2500)
async def run(b,tag,vp,mob):
  c=await b.new_context(viewport=vp,is_mobile=mob,has_touch=mob); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3800)
  await pg.evaluate("()=>{window.__v2.setView('list'); window.__setNum('pct')}"); await pg.wait_for_timeout(2500)
  await pick(pg,'bar'); s=await pg.evaluate(R); ck(tag+" single entity, one year: bar cannot be chosen",s['mode']!='bar',s['mode'])
  o=await pg.evaluate(OPTS); ck(tag+" single entity, one year: chart options = pie only (no bar)",'bar' not in o and 'pie' in o,o)
  await pick(pg,'pie'); s=await pg.evaluate(R); ck(tag+" one big pie, no list rows",s['mode']=='pie' and s['pie'] and s['rows']==0 and not s['la'],s)
  if s['pie'] and vp['width']<600:
    p=s['pie']; cx=(p[0]+p[2])/2; S=p[2]-p[0]
    ck(tag+f" pie centred between x=52 and the right edge (cx {cx:.1f} vs {(52+s['vw'])/2:.1f}), large (S={S:.0f})",abs(cx-(52+s['vw'])/2)<=2 and S>=0.75*(s['vw']-52),p)
    hit=[x for x in s['btns']+s['imgs'] if ov(p,x,1)]; ck(tag+" pie clear of the thumbnails and floating buttons",not hit,hit)
  await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll&&window.__ySelectAll(); }"); await pg.wait_for_timeout(3000)
  s=await pg.evaluate(R); ck(tag+" two years: the single entity switches to the line chart",s['mode']=='line',s['mode'])
  o=await pg.evaluate(OPTS); ck(tag+" two years: chart options = line only (no bar)",'bar' not in o and 'line' in o,o)
  for nm in ('pct','num'):
    await pg.evaluate("(m)=>window.__setNum(m)",nm); await pg.wait_for_timeout(2500); s=await pg.evaluate(R)
    g=s['grid']; ax=s['ax']; labs=[a[0] for a in ax]
    ck(f"{tag} line {nm}: 3-5 light hairlines",3<=len(g)<=5 and all(x[0]=='#d6d6db' for x in g),g)
    ck(f"{tag} line {nm}: small mid-gray labels",ax and all(a[2]=='rgb(142, 142, 147)' for a in ax) and len(ax)>=len(g)-1,ax)
    pat=r'^\d+(\.\d)?%$' if nm=='pct' else r'^\d+(\.\d{1,2})?[KM]?$'
    ck(f"{tag} line {nm}: label format ({labs})",labs and all(re.match(pat,l) for l in labs),labs)
    if nm=='num': ck(f"{tag} line num: abbreviated vote counts (K/M)",any(l.endswith('M') or l.endswith('K') for l in labs),labs)
    dx=sorted(set(round((d[0]+d[2])/2) for d in s['dots'])); tk=[round(t) for t in s['ticks']]
    ck(f"{tag} line {nm}: points on the slider's '20/'24 x positions",len(dx)==2 and len(tk)>=2 and abs(dx[0]-tk[0])<=1.5 and abs(dx[-1]-tk[-1])<=1.5,[dx,tk])
    bad=[(a[0],x) for a in ax for x in s['imgs']+s['btns'] if ov(a[1],x)]; ck(f"{tag} line {nm}: axis labels clear of thumbnails and buttons",not bad,bad)
    gb=[(x[1],y) for x in g for y in s['imgs']+s['btns'] if ov([x[1][0],x[1][1]-0.5,x[1][2],x[1][3]+0.5],y)]; ck(f"{tag} line {nm}: hairlines clear of thumbnails and buttons",not gb,gb)
    bd=[(a[0]) for a in ax for d in s['dots'] if ov(a[1],d)]; ck(f"{tag} line {nm}: axis labels clear of the line points",not bd,bd)
    await pg.screenshot(path=f"/workspace/pv/t1556/sec-{tag}-line-{nm}.png")
  # plural row -> bar list is allowed again
  await pg.evaluate("()=>{const c=document.querySelector('#ysl .tk i'); window.__setNum('pct'); const ys=document.getElementById('yslider'); ys.value=2; ys.dispatchEvent(new Event('input',{bubbles:true}))}"); await pg.wait_for_timeout(1500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1600); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
  await pick(pg,'bar'); s=await pg.evaluate(R); ck(tag+" 'Alabama counties' plural list: bar chart available with list rows",s['la'] and s['mode']=='bar' and s['rows']>=60,{k:s[k] for k in ('la','mode','rows')})
  ck(tag+" no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"ph",{"width":390,"height":844},True); await run(b,"dk",{"width":1280,"height":800},False)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
