# Build 1576 (user, live 1575 desktop Safari, Blount County, AL): (1) thumbnails shrank to ~15px with no % badge: the size followed the crumb flag IMAGE width
# (Alabama's flag is portrait, 14.7px); (2) [Blount solid fill: colour-scale preview pending, not in this build];
# (3) precinct geometry precision; (4) geo filter county rows: state silhouette + star (no generic placeholder, never the building icon).
import asyncio,sys,json,re,os,glob
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
TH="""()=>[...document.querySelectorAll('#cands .cand, #laCands .lact')].filter(b=>b.getBoundingClientRect().width>0).map(b=>{const i=b.querySelector('img'); const r=(i||b).getBoundingClientRect(); const p=b.querySelector('.cs,.cpt'); return {w:r.width,h:r.height,badge:p?p.textContent:'',bd:p?getComputedStyle(p).display:'none'}})"""
PANE="""()=>{let best=0; document.querySelectorAll('.leaflet-pane canvas').forEach(cv=>{ try{ const g=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data; const B=new Map(); let n=0; for(let i=0;i<g.length;i+=4*7){ if(g[i+3]<200) continue; const r=g[i],G=g[i+1],b=g[i+2]; if(!(r>G+40&&r>b+40)) continue; n++; const k=(r>>3)+','+(G>>3)+','+(b>>3); B.set(k,(B.get(k)||0)+1);} const c=[...B.values()].filter(v=>v>n*0.01).length; if(c>best) best=c; }catch(e){} }); return best;}"""
async def blount(b,W,H,mob,eng):
    c=await b.new_context(viewport={'width':W,'height':H},is_mobile=mob,has_touch=mob); pg=await c.new_page()
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Alabama';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Blount County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(8000)
    th=await pg.evaluate(TH); ck(len(th)>=2 and all(abs(t['w']-30)<=1 and abs(t['h']-30)<=1 for t in th) and all(t['badge'] and t['bd']!='none' for t in th),f"{eng} {W}x{H} Blount map: thumbnails a fixed 30px with % badges",th)
    await c.close()
async def main():
  async with async_playwright() as p:
    for eng in ('chromium','webkit'):
      b=await getattr(p,eng).launch()
      for W,H,mob in ((700,800,False),(1280,800,False),(1024,653,False),(390,844,True)):
        if eng=='webkit' and W in (1024,): continue
        await blount(b,W,H,mob,eng)
      await b.close()
    b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':768}); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>[...document.querySelectorAll('li')].find(l=>/^\\d*Alabama/.test(l.textContent.trim())&&l.offsetParent).click()"); await pg.wait_for_timeout(5000)
    r=await pg.evaluate("()=>[...document.querySelectorAll('.foldlist li')].filter(l=>l.offsetParent&&/County/.test(l.textContent)&&!l.classList.contains('la-row')).map(l=>{const o=l.querySelector('.oic'); return o?o.innerHTML:''})")
    ck(len(r)>=10 and all('fill="#222"' in h or 'currentColor' in h for h in r) and all('polygon' in h for h in r),f"AL county rows in the geo filter: silhouette with a star ({len(r)} rows)",[h[:80] for h in r[:2]])
    ck(not any('M4 4h7v6h9v10H9v-6H4z' in h or 'M10 21V4h8v17' in h for h in r),"AL county rows: no placeholder or building glyph",[h[:80] for h in r[:2]])
    bld=await pg.evaluate("()=>[...document.querySelectorAll('svg path')].filter(p=>(p.getAttribute('d')||'').includes('M10 21V4h8v17')&&p.getBoundingClientRect().width>0).length")
    ck(bld==0,"no visible building icon anywhere",bld)
    ck(not er,"no page errors",er[:3]); await b.close()
  here=os.path.dirname(os.path.abspath(__file__)); s=open(os.path.join(here,'..','v2','data','precincts2024','Alabama.js')).read()
  m=re.search(r'\[\[\[(-?\d+),(-?\d+)',s); ck(m and len(m.group(1).lstrip('-'))>=6,"precincts2024 geometry keeps 1e-4 degree precision (unchanged since 1570)",m and m.group(0))
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
