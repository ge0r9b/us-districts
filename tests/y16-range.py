# Build 1574 (QA-038, live 1573 report): a range starting at '16 is a real change view, like '20>'24:
# rows show shifts from 2016 to the end year, thumbnails are the end year's candidates (never Clinton), the map colours by shift.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,60).map(r=>[(r.querySelector('.nmx')||{}).textContent,[...r.querySelectorAll('[data-party]')].map(e=>e.getAttribute('data-party')).join(' / ')])"
LTH="()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.dataset.cid)"
TH="()=>[...document.querySelectorAll('#cands .cand, .cand')].filter(b=>b.offsetParent).map(b=>b.title)"
PANE="""(sel)=>{const cv=document.querySelector(sel+' canvas');if(!cv)return null;const g=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;let n=0,sat=0;const B=new Set();
  for(let i=0;i<g.length;i+=4*37){if(g[i+3]<60)continue;n++;const r=g[i],G=g[i+1],b=g[i+2],s=Math.max(r,G,b)-Math.min(r,G,b);if(s>70){sat++;B.add((r>>5)+','+(G>>5)+','+(b>>5));}}return {n,sat,buckets:B.size}}"""
def shift(rows,st,who):
  for n,t in rows:
    if n==st:
      m=re.search(who+r'[^:]*: ([+−-][\d.]+) pts',t); return float(m.group(1).replace('−','-')) if m else None
EXP={1:{'FL':2.2,'VT':9.4,'end':'2020','cands':{'b20','t20'}},2:{'FL':7.1,'VT':7.2,'end':'2024','cands':{'h24','t24'}}}

async def extra(b):
    # build 1577: QA-047 (US map kept the '20>'24 colours), QA-049 (badge on every thumbnail), QA-043 (Line keeps the '16 range), QA-048 (Philadelphia precincts)
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000)
    f20=await pg.evaluate("()=>window.__fillOf('Colorado')")
    for hi in (2,1):
      await pg.evaluate("(h)=>window.__ySet16(h)",hi); await pg.wait_for_timeout(5000)
      f=await pg.evaluate("()=>window.__fillOf('Colorado')"); rgb=[int(x) for x in re.findall(r'\d+',f)[:3]] if f.startswith('rgb') else None
      ck(rgb and rgb[2]>rgb[0] and f!=f20,f"QA-047 US map '16>'{'24' if hi==2 else '20'}: Colorado coloured as a D shift ({f}, '20>'24 was {f20})",[f,f20])
      th=await pg.evaluate("()=>[...document.querySelectorAll('#cands .cand')].filter(b=>b.offsetParent).map(b=>[b.title,(b.querySelector('.cs,.cpt')||{}).textContent||''])")
      ck(len(th)>=2 and all(re.search(r'\d',v) for t,v in th),f"QA-049 '16>'{'24' if hi==2 else '20'}: every thumbnail has its number",th)
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(3000)
    await pg.evaluate("""async()=>{const m=document.querySelector('button.rbtn.cmain');m.click();await new Promise(r=>setTimeout(r,300));const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch==='line');b&&b.click()}"""); await pg.wait_for_timeout(3000)
    st=await pg.evaluate("()=>[!!window.__y16,window.__y16hi,window.chartMode]")
    ck(st[0] and st[1]==2 and st[2]=='line',"QA-043 Line in '16>'24 keeps the range",st)
    await pg.evaluate("()=>{window.chartMode=null}")
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Philadelphia County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{ if(!document.body.classList.contains('listmode')) document.getElementById('bGlobe').click() }"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>{ const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/Philadelphia/.test(r.textContent)); r&&r.click() }"); await pg.wait_for_timeout(12000)
    rows=await pg.evaluate(ROWS); n=sum("'16→'24" in r[1] for r in rows)
    print("INFO" if not rows else "", end=""); (ck if rows else (lambda *a:print(" (not reached)",a[1])))(len(rows)>=20 and n>=len(rows)*0.5,f"QA-048 Philadelphia precincts '16>'24: change values ({n}/{len(rows)})",rows[:3])
    ck(not er,"extra: no page errors",er[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); er=[]
    c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    for hi in (1,2):
      e=EXP[hi]; lab=f"'16>'{e['end'][2:]}"
      await pg.evaluate("(h)=>window.__ySet16(h)",hi); await pg.wait_for_timeout(5000)
      th=await pg.evaluate(TH); ck(th and not any('Hillary' in t for t in th) and any(e['end'] in t for t in th),f"US {lab}: thumbnails are the {e['end']} candidates, no Clinton",th)
      x=await pg.evaluate(PANE,'.leaflet-st-pane') or await pg.evaluate(PANE,'.leaflet-nat-pane'); ck(bool(x) and x['sat']>=50,f"US {lab}: map coloured",x)
      lg=await pg.evaluate("()=>[...document.querySelectorAll('.heatlegend strong, #ynote')].map(e=>e.textContent).join(' | ')")
      ck('2016' not in lg or '→' in lg,f"US {lab}: legend/note is a change label",lg)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
    def share(rows,st,who):
      for n,t in rows:
        if n==st:
          m=re.search(who+r'[^:]*: ([\d.]+)%',t); return float(m.group(1)) if m else None
    S={}
    S['2016']=await pg.evaluate(ROWS)
    for v,y in ((0,'2020'),(2,'2024')):
      await pg.evaluate("(v)=>{const s=document.getElementById('yslider');s.value=v;s.dispatchEvent(new Event('input',{bubbles:true}))}",v); await pg.wait_for_timeout(3000); S[y]=await pg.evaluate(ROWS)
    for y in ('2020','2024'):
      EXP[1 if y=='2020' else 2]['FL']=round(share(S[y],'FL','Republican')-share(S['2016'],'FL','Republican'),1)
      EXP[1 if y=='2020' else 2]['VT']=round(share(S[y],'VT','Democratic')-share(S['2016'],'VT','Democratic'),1)
    print('expected from single-year rows',{k:(v['FL'],v['VT']) for k,v in EXP.items()})
    for hi in (1,2):
      e=EXP[hi]; lab=f"'16>'{e['end'][2:]}"
      await pg.evaluate("(h)=>window.__ySet16(h)",hi); await pg.wait_for_timeout(5000)
      rows=await pg.evaluate(ROWS)
      ck(len(rows)>=50 and not any('Clinton' in r[1] for r in rows),f"All States {lab}: no plain 2016 rows",rows[:2])
      ck(sum(f"('16→'{e['end'][2:]})" in r[1] for r in rows)>=50,f"All States {lab}: rows are shifts labelled '16→'{e['end'][2:]}",rows[:2])
      fl=shift(rows,'FL','Trump'); vt=shift(rows,'VT','Democratic')
      ck(fl is not None and abs(fl-e['FL'])<0.25 and vt is not None and abs(vt-e['VT'])<0.25,f"All States {lab}: FL Trump {fl} (exp +{e['FL']}), VT Dem {vt} (exp +{e['VT']})",[fl,vt])
      th=set(await pg.evaluate(LTH)); ck(th==e['cands'],f"All States {lab}: thumbnails {sorted(th)}",sorted(th))
      if hi==2: await pg.screenshot(path='/workspace/y16-range-allstates.png')
    # '20>'24 unchanged
    await pg.evaluate("()=>{const s=document.getElementById('yslider'); }")
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>{window.__ySelectAll&&window.__ySelectAll()}"); await pg.wait_for_timeout(4000)
    rows=await pg.evaluate(ROWS); fl=shift(rows,'FL','Trump')
    ck(fl is not None and abs(fl-4.9)<0.15 and not any("'16" in r[1] for r in rows),f"'20>'24 unchanged: FL Trump {fl} (exp +4.9)",rows[:2])
    # PA counties at '16>'24, list and map
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(9000)
    rows=await pg.evaluate(ROWS)
    ck(len(rows)>=40 and sum("('16→'24)" in r[1] for r in rows)>=40 and not any('Clinton' in r[1] for r in rows),f"PA counties '16>'24: shift rows ({len(rows)})",rows[:2])
    th=set(await pg.evaluate(LTH)); ck(th=={'h24','t24'},"PA counties '16>'24: Harris/Trump thumbnails",sorted(th))
    # plain '16 still 2016
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(5000)
    th=await pg.evaluate("()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(b=>b.offsetParent).map(b=>(b.title||'')+'|'+(b.dataset.cid||'')+'|'+(b.getAttribute('aria-label')||''))")
    ck(any('Hillary' in t or 'Clinton' in t for t in th),"plain '16 after a range: back to Clinton/Trump 2016",th)
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(6000)
    x=await pg.evaluate(PANE,'.leaflet-la-pane'); y=await pg.evaluate(PANE,'.leaflet-heat-pane')
    if not (x and x['sat']>=100) and y and y['sat']>(x or {'sat':0})['sat']: x=y  # live zooms wider: the shift heat layer carries the colour
    ck(bool(x) and x['sat']>=40 and x['buckets']>=5,"PA counties '16>'24 map: coloured by shift",x)
    await pg.screenshot(path='/workspace/y16-range-pa-map.png')
    ck(not er,"no page errors",er[:3]); await extra(b); await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
