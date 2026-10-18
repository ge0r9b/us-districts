# Build 1571 (urgent, live 1570 bug): at '16 every level shows 2016 numbers: US (Clinton ~48.2 / Trump ~46.1), a state, a county,
# in the thumbnails (map + list), list rows, and the pie and bar charts; district lists (US House, senate, state house, schools) and precincts too.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
TH="()=>[...document.querySelectorAll('#cands .cand, .cand')].filter(b=>b.offsetParent).map(b=>[b.title,(b.querySelector('.cs,.cpt')||{}).textContent||''])"
CH="""()=>{const p=document.querySelector('.cpanel');const svg=[...document.querySelectorAll('.cpanel svg, .cwideWrap svg')].filter(e=>e.getBoundingClientRect().width>30);
 const bars=[...document.querySelectorAll('.cpanel .sebr i, .cpanel i.rep, .cpanel i.dem, .cwideWrap i')].filter(e=>e.getBoundingClientRect().width>1);
 return {panel:!!p,svg:svg.length,arcs:svg.reduce((n,s)=>n+s.querySelectorAll('circle,path').length,0),bars:bars.length,txt:(p?p.innerText:'').slice(0,200)}}"""
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,40).map(r=>[(r.querySelector('.nmx')||{}).textContent,[...r.querySelectorAll('[data-party]')].map(e=>e.getAttribute('data-party')).join(' / ')])"
PICK="""async(k)=>{const m=document.querySelector('button.rbtn.cmain');if(window.chartMode===k)return;m.click();await new Promise(r=>setTimeout(r,300));const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch===k);if(b)b.click();else if(m.dataset.ch===k)m.click()}"""
def pct(th,who):
  for t,v in th:
    if t.startswith(who) and t.endswith('2016'):
      m=re.search(r'([\d.]+)%',v); return float(m.group(1)) if m else None
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page()
    er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(4000)
    th=await pg.evaluate(TH); ck(len(th)==2 and all(re.search(r'\d',v) for t,v in th),"US map view: Clinton / Trump thumbnails show 2016 %",th)
    for mode in ('pie','bar'):
      await pg.evaluate(PICK,mode); await pg.wait_for_timeout(2500)
      th=await pg.evaluate(TH); cl,tr=pct(th,'Hillary'),pct(th,'Donald')
      ck(cl is not None and tr is not None and abs(cl-48.2)<0.4 and abs(tr-46.1)<0.4,f"US {mode}: thumbnails Clinton {cl} / Trump {tr} (~48.2 / 46.1)",th)
      ch=await pg.evaluate(CH); ck(ch['svg']>=1 and ch['arcs']>=2 if mode=='pie' else ch['bars']>=2,f"US {mode} chart is drawn",ch)
    await pg.evaluate("()=>{window.chartMode=null;}")
    # state, then county (scope = the selection; the list shows its children)
    for lvl,js in (("PA","()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"),
                   ("Philadelphia County","()=>{const c=document.getElementById('county');c.value='Philadelphia County';c.onchange&&c.onchange()}")):
      await pg.evaluate(js); await pg.wait_for_timeout(7000)
      for mode in ('pie','bar'):
        await pg.evaluate(PICK,mode); await pg.wait_for_timeout(2500)
        th=await pg.evaluate(TH); ck(len(th)>=2 and all(re.search(r'\d',v) for t,v in th[:2]),f"{lvl} {mode}: thumbnails show 2016 values",th)
        ch=await pg.evaluate(CH); ck(ch['svg']>=1 and ch['arcs']>=2 if mode=='pie' else ch['bars']>=2,f"{lvl} {mode} chart is drawn",ch)
    await pg.screenshot(path='/workspace/y2016-levels-county.png'); await c.close()
    # list levels: All States -> PA counties -> Philadelphia County children; rows, thumbnails, row pies and bars; then district lists
    LTH="()=>[...document.querySelectorAll('#laCands .lact')].map(b=>[b.dataset.cid,(b.querySelector('.cpt')||{}).textContent||''])"
    RCH="()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].slice(0,10);return {n:r.length,pies:r.filter(x=>x.querySelector('.pwr svg circle')).length,bars:r.filter(x=>[...x.querySelectorAll('[data-party]')].some(e=>e.getBoundingClientRect().width>2)).length}}"
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
    for lvl,nxt in (("All States","PA"),("PA counties","Philadelphia County"),("Philadelphia County children",None)):
      rows=await pg.evaluate(ROWS); n=sum('Clinton' in r[1] for r in rows)
      ck(len(rows)>=1 and n>=max(1,len(rows)*0.6),f"{lvl} list at '16: rows show 2016 values ({n}/{len(rows)})",rows[:3])
      th=await pg.evaluate(LTH); ck(len(th)==2 and all(re.search(r'\d',v) for k,v in th),f"{lvl}: thumbnails show 2016 values",th)
      for mode in ('pie','bar'):
        await pg.evaluate(PICK,mode); await pg.wait_for_timeout(2500); r=await pg.evaluate(RCH)
        ck(r['n']>=1 and (r['pies'] if mode=='pie' else r['bars'])>=max(1,r['n']*0.6),f"{lvl} {mode}: rows draw 2016 {mode}s",r)
      await pg.evaluate(PICK,'bar'); await pg.wait_for_timeout(800); await pg.evaluate("()=>{const m=document.querySelector('button.rbtn.cmain');m.click()}"); await pg.wait_for_timeout(300)
      await pg.evaluate("()=>{const d=document.getElementById('chartDim');d&&d.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))}"); await pg.wait_for_timeout(1500)
      if lvl=="PA counties": await pg.screenshot(path='/workspace/y2016-levels-pa.png')
      if nxt: await pg.evaluate("(n)=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent===n||r.querySelector('b.rn').title===n).click()",nxt); await pg.wait_for_timeout(9000)
    await c.close()
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
    base=dict((r[0],r[1]) for r in await pg.evaluate(ROWS))
    # live 1570 report, fresh page: go straight from 2020/24 to a '16-'20 range (y16d never set before)
    c3=await b.new_context(viewport={'width':1024,'height':768},device_scale_factor=1); p3=await c3.new_page(); p3.on('pageerror',lambda e:er.append(str(e)))
    await p3.goto(U,wait_until="networkidle"); await p3.wait_for_timeout(3500)
    await p3.evaluate("()=>document.getElementById('bGeo').click()"); await p3.wait_for_timeout(1200)
    await p3.evaluate("()=>document.querySelector('li.la-row').click()"); await p3.wait_for_timeout(6000)
    await p3.evaluate("()=>window.__ySet16(1)"); await p3.wait_for_timeout(5000)
    rows=await p3.evaluate(ROWS); n=sum('Clinton' in r[1] for r in rows); ld=await p3.evaluate("()=>getComputedStyle(document.querySelector('#listView .lvgrid'),'::before').content")
    ck(len(rows)>=40 and n>=40 and 'Loading' not in ld,f"fresh page, All States, '16-'20 range: values, not stuck loading ({n}/{len(rows)})",[ld,rows[:2]])
    await c3.close()
    # live 1570 report: All States at a '16-'20 range was stuck on 'Loading 2016 results…' with 2020/24 order and no values
    def clv(r):
      m=re.search(r'Clinton\)?: ?([\d,.]+)',r[1]); return float(m.group(1).replace(',','')) if m else None
    od=[clv(r) for r in await pg.evaluate(ROWS)][:8]
    ck(all(x is not None for x in od) and od==sorted(od,reverse=True),"All States at '16: rows sorted by 2016 Clinton values",od)
    for hi in (1,2):
      await pg.evaluate("(h)=>window.__ySet16(h)",hi); await pg.wait_for_timeout(4000)
      rows=await pg.evaluate(ROWS); n=sum('Clinton' in r[1] for r in rows); ld=await pg.evaluate("()=>getComputedStyle(document.querySelector('#listView .lvgrid'),'::before').content")
      ck(len(rows)>=40 and n>=40 and 'Loading' not in ld,f"All States at a '16-{'20' if hi==1 else '24'} range: values, not stuck loading ({n}/{len(rows)})",[ld,rows[:2]])
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(3000)
    for k in ('ushouse','senate','statehouse','schools'):
      await pg.evaluate("(k)=>{const b=document.querySelector('#lyrRow .lbtn[data-k=\"'+k+'\"]');if(b)b.click()}",k); await pg.wait_for_timeout(6000)
      rows=await pg.evaluate(ROWS); n=sum('Clinton' in r[1] for r in rows)
      ck(len(rows)>=5 and n>=len(rows)*0.6,f"{k} list at '16: 2016 values ({n}/{len(rows)} rows)",rows[:3])
      if k!='ushouse':
        same=[r for r in rows if r[0] in base]; diff=[r for r in same if r[1]!=base[r[0]]]
        ck(len(same)>=10 and not diff,f"QA-017/029 {k}: state rows equal the All States list at '16",diff[:2])
      await pg.evaluate("(k)=>{const b=document.querySelector('#lyrRow .lbtn[data-k=\"'+k+'\"]');if(b&&b.classList.contains('on'))b.click()}",k); await pg.wait_for_timeout(1500)
    await c.close()
    # map fills at '16 (live 1571 report: "heat map from 2016 is not colored"): every pane that draws results must show real D/R fills
    PANE="""(sel)=>{const cv=document.querySelector(sel+' canvas');if(!cv)return null;const g=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;let n=0,sat=0;const B=new Set();
      for(let i=0;i<g.length;i+=4*37){if(g[i+3]<60)continue;n++;const r=g[i],G=g[i+1],b=g[i+2],s=Math.max(r,G,b)-Math.min(r,G,b);if(s>70){sat++;B.add((r>>5)+','+(G>>5)+','+(b>>5));}}return {n,sat,buckets:B.size}}"""
    def colored(x,minsat=100,minb=4): return bool(x) and x['sat']>=minsat and x['sat']>=0.4*x['n'] and x['buckets']>=minb
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(5000)
    x=await pg.evaluate(PANE,'.leaflet-st-pane') or await pg.evaluate(PANE,'.leaflet-nat-pane'); ck(colored(x),"US map at '16: states coloured D/R",x)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(8000)
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(6000)
    x=await pg.evaluate(PANE,'.leaflet-la-pane'); ck(colored(x,300,6),"PA counties map at '16 (from the list): each county coloured D/R, not one pale fill",x)
    await pg.screenshot(path='/workspace/y2016-map-pa.png')
    x=await pg.evaluate(PANE,'.leaflet-heat-pane'); ck(colored(x),"PA county heat layer at '16 coloured",x)
    await c.close()
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(2000)
    await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=\"ushouse\"]');if(b)b.click()}"); await pg.wait_for_timeout(7000)
    if await pg.evaluate("()=>document.body.classList.contains('listmode')"): await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(5000)
    x=None
    for sel in ('.leaflet-type-pane','.leaflet-nat-pane','.leaflet-la-pane'):
      y=await pg.evaluate(PANE,sel)
      if colored(y): x=y; break
    ck(colored(x),"US House map at '16: districts coloured D/R",x)
    await pg.screenshot(path='/workspace/y2016-map-cd.png'); await c.close()
    ck(not er,"no page errors",er[:3]); await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
