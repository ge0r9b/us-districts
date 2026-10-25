# pass 33 (build 1611): quick fresh-state check: thumbnails '16/'20/'24, __stTot, US House + senate lists (% and #), rows vs header
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
HDR="()=>({crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),num:window.__numMode&&window.__numMode()})"
async def main():
  eng=sys.argv[1]; states=sys.argv[2].split(','); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for st in states:
      c,pg,log=await ctx(b,390,844,True,eng); R=out[st]={}
      async def tap(sel,wait=0):
        xy=await center(pg,sel)
        if not xy: return None
        v=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return v
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
      await typegq(pg,st); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      R['hdr']=await pg.evaluate(HDR)
      R['tot']=await pg.evaluate("n=>{const o={};for(const y of ['2016','2020','2024']){try{o[y]=window.__stTot(n,y)}catch(e){o[y]=String(e).slice(0,80)}}return o}",st)
      yrs={}
      for i,y in [(0,'2016'),(1,'2020'),(2,'2024')]:
        await pg.evaluate(f"()=>window.__ySetYr({i})"); await pg.wait_for_timeout(1800); yrs[y]=await pg.evaluate(TH)
      R['thumbs_by_year']=yrs
      await safeshot(pg,f"../shots/b1612p33-{eng[:2]}-390x844-q-{st.replace(' ','')}-map.png")
      R['types']={}
      for k in ['ushouse','senate']:
        T=R['types'][k]={}
        await tap('#bLyr',900); T['lat']=await tap(f'#lyrRow .lbtn[data-k={k}]',4000)
        if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
        T['map_th']=await pg.evaluate(TH)
        await tap('#bGlobe',4000); T['hdr']=await pg.evaluate(HDR); T['th']=await pg.evaluate(TH); T['rows']=(await pg.evaluate(ROWS))[:60]
        await safeshot(pg,f"../shots/b1612p33-{eng[:2]}-390x844-q-{st.replace(' ','')}-{k}-list.png")
        await pg.evaluate("()=>window.__setNum&&window.__setNum('num')"); await pg.wait_for_timeout(1500)
        T['num']=await pg.evaluate("()=>window.__numMode()"); T['th_num']=await pg.evaluate(TH); T['rows_num']=(await pg.evaluate(ROWS))[:60]
        await safeshot(pg,f"../shots/b1612p33-{eng[:2]}-390x844-q-{st.replace(' ','')}-{k}-list-num.png")
        await pg.evaluate("()=>window.__setNum&&window.__setNum('pct')"); await pg.wait_for_timeout(800)
        await tap('#bGlobe',3000); await tap('#bLyr',900); await tap(f'#lyrRow .lbtn[data-k={k}]',3000)
        if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
      R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]+log['reqfail'][:4]+log['http'][:4]
      print(st,json.dumps(R)[:3000],flush=True); await c.close()
      json.dump(out,open(f"b1612p33-quick-{eng}-390x844.json",'w'),indent=1)
    await b.close()
asyncio.run(main())
