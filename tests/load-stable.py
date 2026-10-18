# usage: python3 tests/load-stable.py URL -- build 1557: nothing jumps on page load (t282).
# A restored non-default view (another state, list, chart, ...) is applied step by step after load; html.boot keeps the results area
# blank (list-gray + small spinner, no fade) until the restore has finished and the UI rects are stable, then shows it at once.
# Budget: CLS (layout-shift API, Chromium, 390x844 phone) < 0.01 per scenario; no visible key UI object changes position after it
# is first shown (rAF sampling, catches fixed/transform moves CLS ignores); the boot cover is released (< 12 s); WebKit: cover released.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(m,c,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:600])); (None if c else F.append(m))
INIT=r"""
window.__ls=[]; try{ new PerformanceObserver(l=>{ for(const e of l.getEntries()) window.__ls.push({t:Math.round(e.startTime),v:e.value,inp:e.hadRecentInput}); }).observe({type:'layout-shift',buffered:true}); }catch(e){}
window.__mv={}; const SEL=['.rbtn','#bLyr','.tlab','#cands img','#laCands .lact','#bBack','#laSort','#barGeo .fsq','#crumbs','.lvrow.la','.cpanel svg','#chartLg'];
(function f(){ try{ const now=Math.round(performance.now()); const boot=document.documentElement.classList.contains('boot');
  SEL.forEach(s=>{ document.querySelectorAll(s).forEach((e,i)=>{ if(i>3) return; const r=e.getBoundingClientRect(); const st=getComputedStyle(e); const vis=!boot&&r.width>0&&st.visibility!=='hidden'&&r.bottom>0&&r.top<innerHeight;
    const k=s+'#'+i, v=vis?[r.x,r.y,r.width,r.height].map(Math.round).join(','):'-'; const a=window.__mv[k]||(window.__mv[k]=[]); if(!a.length||a[a.length-1][1]!==v) a.push([now,v]); }); }); }catch(e){} if(performance.now()<14000) requestAnimationFrame(f); })();
"""
def moves(mv):
  out=[]
  for k,a in mv.items():
    seen=[x for x in a if x[1]!='-']
    # a visible object that later shows at another rect without disappearing in between = a jump
    for p,q in zip(a,a[1:]):
      if p[1]!='-' and q[1]!='-' and p[1]!=q[1]: out.append([k,p,q])
  return out
async def scenario(b,name,setup,engine='chromium'):
  c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=engine=='chromium',has_touch=True)
  pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
  await pg.goto(U,wait_until="networkidle"); await pg.evaluate("()=>localStorage.clear()"); await pg.goto(U.split('#')[0]+"#",wait_until="networkidle"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(2500)
  await setup(pg); await pg.wait_for_timeout(2500); await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()")
  await c.add_init_script(INIT); await pg.goto("about:blank"); await pg.goto(U.split('#')[0],wait_until="load"); await pg.wait_for_timeout(11000)
  ls=await pg.evaluate("window.__ls"); mv=await pg.evaluate("window.__mv"); bd=await pg.evaluate("window.__bootDone||null"); boot=await pg.evaluate("document.documentElement.classList.contains('boot')")
  cls=sum(e['v'] for e in ls if not e['inp'])
  if engine=='chromium':
    ck(f"{name}: CLS {cls:.4f} < 0.01",cls<0.01,ls)
    mvs=[m for m in moves(mv) if not m[0].startswith('.lvrow')]  # list rows legitimately re-render values; their position is covered by CLS
    ck(f"{name}: no visible UI object jumps after it is shown",not mvs,mvs[:6])
  ck(f"{name} [{engine}]: boot cover released (boot={'restored' if bd else 'not needed'}, {bd} ms)",not boot and (bd is None or bd<12500),[boot,bd])
  ck(f"{name} [{engine}]: no page errors",not er,er[:3]); await c.close(); return cls
async def none(pg): pass
async def mpa(pg): await pg.evaluate("()=>{state.value='Pennsylvania'; state.onchange&&state.onchange();}"); await pg.wait_for_timeout(4000)
async def lst(pg):
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(6000)
async def pie(pg):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
  await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='pie'); x&&x.click();}"); await pg.wait_for_timeout(1500)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); R={}
    for n,f in (('default map',none),('restored PA map',mpa),('restored PA county list',lst),('restored single-entity pie',pie)): R[n]=await scenario(b,n,f)
    await b.close()
    try:
      w=await p.webkit.launch(); await scenario(w,'restored PA county list',lst,'webkit'); await w.close()
    except Exception as e: print("SKIP webkit:",str(e)[:120])
    print("CLS",json.dumps({k:round(v,4) for k,v in R.items()}))
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
