# Oct 25 8PM (1621): At-large labels in AK/WY/VT/DE/ND/SD/DC, earliest year ('16) drill-ins, 320 line-chart clipping, thumbnail axis, console errors
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
src=open('h1800-own.py').read()
exec(src[src.index('AX='):src.index('S16=')])
HDR="()=>({title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),ym:window.__ymode&&window.__ymode()})"
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,4)"
ALLROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).slice(0,8).map(r=>r.innerText.replace(/\\n/g,' | '))"
CLIP="""()=>{const cb=document.getElementById('chartBox');if(!cb)return null;const B=cb.getBoundingClientRect();const o={box:[B.left,B.top,B.width,B.height].map(Math.round),vw:innerWidth,out:[],ovl:[]};const T=[...cb.querySelectorAll('text,span,div')].filter(e=>e.childElementCount==0&&e.textContent.trim()&&e.getBoundingClientRect().width>0);const R=T.map(e=>{const r=e.getBoundingClientRect();return [e.textContent.trim().slice(0,12),r.left,r.top,r.right,r.bottom]});for(const r of R){if(r[1]<B.left-1||r[3]>B.right+1||r[2]<B.top-1||r[4]>B.bottom+1||r[1]<0||r[3]>innerWidth)o.out.push(r.map(x=>typeof x=='number'?Math.round(x):x))}for(let i=0;i<R.length;i++)for(let j=i+1;j<R.length;j++){const a=R[i],b=R[j];const ox=Math.min(a[3],b[3])-Math.max(a[1],b[1]),oy=Math.min(a[4],b[4])-Math.max(a[2],b[2]);if(ox>2&&oy>2)o.ovl.push([a[0],b[0],Math.round(ox),Math.round(oy)])}o.texts=R.map(r=>r[0]);return o}"""
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; parts=sys.argv[3].split(','); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsb1621/b1621h20-{eng[:2]}-{W}x{H}"
    async def tap(sel,wait=0):
      xy=await center(pg,sel)
      if not xy: return None
      v=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return v
    async def tolist(want):
      if (await pg.evaluate(HDR))['list']!=want: await tap('#bGlobe',4000)
    async def geo(q):
      await tolist(False); await typegq(pg,q); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    async def layer(k):
      await tolist(False); await tap('#bLyr',900); l=await tap(f'#lyrRow .lbtn[data-k={k}]',4500)
      if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',700)
      return l
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    if 'al' in parts:
      A=out['atlarge']={}
      await layer('ushouse')
      for st in ['Alaska','Wyoming','Vermont','Delaware','North Dakota','South Dakota','District of Columbia']:
        await geo(st); m=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(AX),await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-tooltip,.dlbl,.leaflet-marker-icon')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()).filter(x=>x).slice(0,6)")]
        await safeshot(pg,f"{pre}-al-{st.replace(' ','')}-map.png")
        await tap('#bGlobe',4500); l=[await pg.evaluate(HDR),await pg.evaluate(ALLROWS),await pg.evaluate(ROWS),await pg.evaluate(TH),await pg.evaluate(AX)]
        await safeshot(pg,f"{pre}-al-{st.replace(' ','')}-list.png")
        A[st]={'map':m,'list':l}; print('AL',st,json.dumps(A[st])[:900],flush=True)
      await layer('ushouse')
    if 'y16' in parts:
      Y=out['y16']={}
      for st,county in [('South Dakota','Minnehaha'),('Oregon','Lane'),('Kentucky','Fayette')]:
        await geo(st); await pg.evaluate("()=>window.__ySetYr(0)"); await pg.wait_for_timeout(2500)
        r={'map':[await pg.evaluate(HDR),await pg.evaluate(TH)]}
        await tap('#bGlobe',4500); await tap('#bGeo',1200); r['lat_counties']=await tap('li.la-row',4500)
        r['counties']=[await pg.evaluate(HDR),await pg.evaluate(ALLROWS),await pg.evaluate(TH)]
        xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",county)
        await pg.wait_for_timeout(400)
        xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",county)
        if xy:
          r['lat_county']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000)
          r['county']=[await pg.evaluate(HDR),await pg.evaluate(ALLROWS),await pg.evaluate(TH),await pg.evaluate(AX)]
          await safeshot(pg,f"{pre}-y16-{st.replace(' ','')}-{county}.png")
          xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent)[0];if(!r)return null;const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
          if xy:
            r['lat_sub']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000); r['sub']=[await pg.evaluate(HDR),await pg.evaluate(ALLROWS),await pg.evaluate(TH)]
            await safeshot(pg,f"{pre}-y16-{st.replace(' ','')}-sub.png")
          await tap('#bGlobe',5000); r['submap']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate("()=>{const m=window.__map;return m?[m.getZoom(),+m.getCenter().lat.toFixed(3),+m.getCenter().lng.toFixed(3)]:null}")]
          await safeshot(pg,f"{pre}-y16-{st.replace(' ','')}-submap.png")
        r['ym_end']=await pg.evaluate("()=>window.__ymode&&window.__ymode()")
        Y[st]=r; print('Y16',st,json.dumps(r)[:1800],flush=True)
        await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(1500)
    if 'line' in parts:
      L=out['line']={}
      for st in ['Oregon','Kentucky','New Mexico']:
        await geo(st)
        if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await tap('#bTime',1000)
        for nm,js in [('16-24','window.__ySet16(2)'),('16-20','window.__ySet16(1)')]:
          await pg.evaluate(f"()=>{{{js}}}"); await pg.wait_for_timeout(2500)
          for num in ['pct','num']:
            await pg.evaluate(f"()=>window.__setNum&&window.__setNum('{num}')"); await pg.wait_for_timeout(1000)
            if not await pg.evaluate("()=>document.getElementById('chartBox').classList.contains('open')"): await tap('#chartBox .cmain',900)
            await tap('#chartBox .copts button[data-ch=line]',2500)
            k=f"{st}-{nm}-{num}"; L[k]={'mode':await pg.evaluate("()=>window.chartMode"),'clip':await pg.evaluate(CLIP),'th':await pg.evaluate(TH)}
            await safeshot(pg,f"{pre}-line-{st.replace(' ','')}-{nm}-{num}.png"); print('LINE',k,json.dumps(L[k])[:900],flush=True)
        await pg.evaluate("()=>window.__setNum&&window.__setNum('pct')"); await pg.evaluate("()=>window.__ySetYr(2)"); await pg.wait_for_timeout(1500)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:8]+log['reqfail'][:4]+log['http'][:4]; print('ERR',out['err'],flush=True)
    json.dump(out,open(f"b1621h2000-fresh-{eng}-{W}x{H}.json",'w'),indent=1); await b.close()
asyncio.run(main())
