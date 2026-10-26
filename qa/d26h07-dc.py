# Oct 26 ~7 AM (1622): DC everywhere: map thumbnails '16/'20/'24 in % and #, every district type offered for DC (list rows, header, % and #), US-level US House list DC row, reload restore
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),lt:(window.__stateSnapshot()||{}).lt})"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"../shots/b1622d26h07-{eng[:2]}-{W}x{H}-dc"
    async def tap(sel,w=0):
      xy=await center(pg,sel)
      if not xy: return None
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
    async def tolist(want):
      if (await pg.evaluate(HDR))['list']!=want: return await tap('#bGlobe',4500)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    out['tot']=await pg.evaluate("()=>['2016','2020','2024'].map(y=>window.__stTot('District of Columbia',y))")
    # US-level US House list: DC row
    await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(1500)
    await tap('#bLyr',900); out['lat_us_ushouse']=await tap('#lyrRow .lbtn[data-k=ushouse]',4500)
    if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
    out['lat_us_list']=await tolist(True); rows=await pg.evaluate(ROWS); out['us_ushouse_n']=len(rows); out['us_ushouse_dc']=[r for r in rows if 'DC' in r or 'Columbia' in r][:3]; out['us_ushouse_al']=[r for r in rows if 'At-large' in r][:10]
    await pg.evaluate("()=>{const e=[...document.querySelectorAll('#listView .lvrow')].find(r=>/DC/.test(r.innerText));e&&e.scrollIntoView({block:'center'})}"); await pg.wait_for_timeout(800)
    await safeshot(pg,f"{pre}-US-ushouse-list-DCrow.png")
    await tolist(False); await tap('#bLyr',900); await tap('#lyrRow .lbtn[data-k=ushouse]',3500)
    if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
    await typegq(pg,'District of Columbia'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5500)
    out['map']=[await pg.evaluate(HDR),await pg.evaluate(TH)]
    yrs={}
    for i,y in [(0,'2016'),(1,'2020'),(2,'2024')]:
      await pg.evaluate(f"()=>window.__ySetYr({i})"); await pg.wait_for_timeout(2200); yrs[y]={'pct':await pg.evaluate(TH)}
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1300); yrs[y]['num']=await pg.evaluate(TH); await safeshot(pg,f"{pre}-map-{y}-num.png")
      await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(900)
    out['years']=yrs
    await tap('#bLyr',900); out['types_offered']=await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow .lbtn')].filter(b=>b.offsetParent).map(b=>b.dataset.k)")
    await safeshot(pg,f"{pre}-types-menu.png"); await tap('#bLyr',800)
    out['types']={}
    for k in out['types_offered']:
      if k in ('none',): continue
      T=out['types'][k]={}
      await tolist(False); await tap('#bLyr',900); T['lat']=await tap(f'#lyrRow .lbtn[data-k={k}]',4500)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
      T['map']=[await pg.evaluate(HDR),await pg.evaluate(TH)]
      T['lat_list']=await tolist(True); T['hdr']=await pg.evaluate(HDR); T['rows']=(await pg.evaluate(ROWS))[:6]; T['th']=await pg.evaluate(TH)
      await safeshot(pg,f"{pre}-{k}-list.png")
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1300); T['rows_num']=(await pg.evaluate(ROWS))[:4]; T['th_num']=await pg.evaluate(TH); await safeshot(pg,f"{pre}-{k}-list-num.png")
      await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(900)
      if k=='ushouse':
        s1=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
        T['reload']={'before':s1,'after':await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"),'hdr':await pg.evaluate(HDR),'rows':(await pg.evaluate(ROWS))[:3],'th':await pg.evaluate(TH)}
        await safeshot(pg,f"{pre}-{k}-list-reload.png")
      await tolist(False); await tap('#bLyr',900); await tap(f'#lyrRow .lbtn[data-k={k}]',3500)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
      print(k,json.dumps(T)[:1500],flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]+log['reqfail'][:4]+log['http'][:4]
    print(json.dumps({k:out[k] for k in out if k!='types'})[:4000],flush=True)
    json.dump(out,open(f"b1622d26h07-dc-{eng}-{W}x{H}.json",'w'),indent=1); await b.close()
asyncio.run(main())
