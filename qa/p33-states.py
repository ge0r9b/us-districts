# pass 31 (build 1609): fresh coverage outside PA/CA/OH: district types, %/# and sort, ranges + chart menu, county > precinct drill, reload restore
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p33-flow.py').read().split('ROWS=')[0].split('from common import *')[1])  # LAYOUT
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
NROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].length"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').placeholder,ym:window.__ymode&&window.__ymode(),num:window.__numMode&&window.__numMode(),list:document.body.classList.contains('listmode'),sort:(()=>{const s=document.getElementById('laSort');if(!s||!s.offsetParent)return null;const r=s.getBoundingClientRect();return [s.innerText,Math.round(r.left),Math.round(r.top)]})()})"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
def order(rows):
  v=[]
  for r in rows:
    m=re.search(r'\|\s*([-+−]?[\d.,]+)\s*(%|K|M)?',r)
    if m:
      x=float(m.group(1).replace(',','').replace('−','-')); x*= {'K':1e3,'M':1e6}.get(m.group(2),1); v.append(x)
  bad=[i for i in range(1,len(v)) if v[i]>v[i-1]+1e-9]
  return {'n':len(v),'first':v[:5],'not_desc_at':bad[:5]}
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; states=sys.argv[3].split(','); parts=sys.argv[4].split(',') if len(sys.argv)>4 else ['types','ranges','drill']
  out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for st,county,pp in [s.split(':') for s in states]:
      parts=pp.split('+')
      c,pg,log=await ctx(b,W,H,W<600,eng); R=out[st]={'lat':{}}; pre=f"../shots/b1612p33-{eng[:2]}-{W}x{H}-st-{st.replace(' ','')}"
      async def tap(sel,wait=0):
        xy=await center(pg,sel)
        if not xy: return None
        v=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return v
      async def tolist(want):
        if (await pg.evaluate(HDR))['list']!=want: await tap('#bGlobe',4000)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      R['map']=[await pg.evaluate(HDR),await pg.evaluate(TH)]
      R['tot']=await pg.evaluate("n=>{const o={};for(const y of ['2016','2020','2024']){try{o[y]=window.__stTot(n,y)}catch(e){o[y]=String(e).slice(0,80)}}return o}",st)
      yrs={}
      for i,y in [(0,'2016'),(1,'2020'),(2,'2024')]:
        await pg.evaluate(f"()=>window.__ySetYr({i})"); await pg.wait_for_timeout(2000); yrs[y]=await pg.evaluate(TH)
      R['thumbs_by_year']=yrs; print(st,'map',R['map'],R['tot'],yrs,flush=True)
      if 'types' in parts:
        R['types']={}
        for k in ['senate','statehouse','schools','ushouse']:
          T=R['types'][k]={}
          await tolist(False); await tap('#bLyr',900)
          T['lat']=await tap(f'#lyrRow .lbtn[data-k={k}]',4500)
          if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
          T['map']=[await pg.evaluate(HDR),await pg.evaluate(TH)]
          T['lat_tolist']=await tap('#bGlobe',4500)
          rows=await pg.evaluate(ROWS); T['n']=await pg.evaluate(NROWS); T['rows']=rows[:6]; T['order']=order(rows); T['hdr']=await pg.evaluate(HDR); T['th']=await pg.evaluate(TH); T['layout']=await pg.evaluate(LAYOUT)
          await safeshot(pg,f"{pre}-{k}-list.png")
          if T['hdr']['sort']: T['lat_sort']=await tap('#laSort',1500); r2=await pg.evaluate(ROWS); T['rows_flip']=r2[:4]; T['order_flip']=order(r2); await tap('#laSort',1500)
          T['lat_num']=await tap('#bNum',1200)
          opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
          if opt: T['lat_numpick']=await tap_latency(pg,*opt); await pg.wait_for_timeout(2000)
          r3=await pg.evaluate(ROWS); T['num']=await pg.evaluate("()=>window.__numMode()"); T['rows_num']=r3[:5]; T['order_num']=order(r3); T['th_num']=await pg.evaluate(TH); T['layout_num']=await pg.evaluate(LAYOUT)
          await safeshot(pg,f"{pre}-{k}-list-num.png")
          await pg.evaluate("()=>window.__setNum&&window.__setNum('pct')"); await pg.wait_for_timeout(1200); T['num_back']=await pg.evaluate("()=>window.__numMode()")
          if k=='statehouse':
            s1=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
            T['reload']={'before':s1,'after':await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'hdr':await pg.evaluate(HDR),'n':await pg.evaluate(NROWS),'rows':(await pg.evaluate(ROWS))[:3]}
            await safeshot(pg,f"{pre}-{k}-list-reload.png")
          await tolist(False); await tap('#bLyr',900); await tap(f'#lyrRow .lbtn[data-k={k}]',3500)
          if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
          T['after_off']=await pg.evaluate(HDR)
          print(st,k,json.dumps({x:T[x] for x in T if x not in('layout','layout_num')})[:1500],'LAYOUT',T['layout'],T['layout_num'],flush=True)
      if 'ranges' in parts:
        await tolist(False); R['ranges']={}
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
        for nm,js in [('16-20','window.__ySet16(1)'),('20-24','window.__ySelectAll()'),('16-24','window.__ySet16(2)')]:
          await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(3000); G=R['ranges'][nm]={'ysl':await pg.evaluate("()=>window.__ysl.get()"),'ym':await pg.evaluate("()=>window.__ymode()"),'th':await pg.evaluate(TH),'charts':{}}
          await tap('#chartBox .cmain',900); opts=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].filter(b=>b.offsetParent).map(b=>b.dataset.ch)"); G['opts']=opts
          for ch in opts:
            if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',900)
            l=await tap(f'#chartBox .copts button[data-ch={ch}]',2500)
            G['charts'][ch]={'lat':l,'mode':await pg.evaluate("()=>window.chartMode"),'txt':await pg.evaluate("()=>document.getElementById('chartBox').innerText.replace(/\\n/g,' | ').slice(0,300)"),'layout':await pg.evaluate(LAYOUT)}
            await safeshot(pg,f"{pre}-range{nm}-{ch}.png")
          print(st,'range',nm,json.dumps(G)[:1500],flush=True)
        await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(2000)
        if await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',600)
      if 'drill' in parts:
        D=R['drill']={}
        await tolist(False); await tap('#bGeo',1200); D['menu']=(await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40))"))[:3]
        D['lat_counties']=await tap('li.la-row',4500); D['hdr1']=await pg.evaluate(HDR); D['n1']=await pg.evaluate(NROWS); r=await pg.evaluate(ROWS); D['rows1']=r[:5]; D['order1']=order(r)
        xy=await pg.evaluate(NMXY,county); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMXY,county)
        if xy:
          D['lat_county']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); D['hdr2']=await pg.evaluate(HDR); D['n2']=await pg.evaluate(NROWS); r=await pg.evaluate(ROWS); D['rows2']=r[:6]; D['order2']=order(r); D['th2']=await pg.evaluate(TH); D['layout2']=await pg.evaluate(LAYOUT)
          await safeshot(pg,f"{pre}-drill-{county.replace(' ','')}.png")
          xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent)[0];if(!r)return null;const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
          if xy:
            D['lat_sub']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); D['hdr3']=await pg.evaluate(HDR); D['n3']=await pg.evaluate(NROWS); r=await pg.evaluate(ROWS); D['rows3']=r[:6]; D['th3']=await pg.evaluate(TH)
            await safeshot(pg,f"{pre}-drill-sub.png")
          await tap('#bGlobe',5000); D['map3']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate("()=>{const m=window.__map;return m?[m.getZoom(),m.getCenter().lat.toFixed(3),m.getCenter().lng.toFixed(3)]:null}"),await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.slice(0,150))")]
          await safeshot(pg,f"{pre}-drill-sub-map.png")
          s1=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
          D['reload']={'before':s1,'after':await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH)}
          await safeshot(pg,f"{pre}-drill-reload.png")
        print(st,'drill',json.dumps(D)[:2500],flush=True)
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]+log['reqfail'][:4]+log['http'][:4]; print(st,'err',R['err'],flush=True)
      await c.close()
      json.dump(out,open(f"b1612p33-states-{eng}-{W}x{H}-{sys.argv[5] if len(sys.argv)>5 else 'x'}.json",'w'),indent=1)
    await b.close()
asyncio.run(main())
