# build 1582 (user): candidate icons keep the map view's spot in map, list, pie, bar and line; no text badge / tooltip by them in chart views
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
Q="""()=>{ const vis=e=>{ const r=e.getBoundingClientRect(); if(!(r.width>0)) return false; let x=e; while(x&&x!==document.body){ const s=getComputedStyle(x); if(s.visibility==='hidden'||s.display==='none'||+s.opacity===0) return false; x=x.parentElement; } return true; };
 const ims=[...document.querySelectorAll('#cands img')].filter(vis).map(i=>{const r=i.getBoundingClientRect(); return [Math.round(r.left*2)/2,Math.round(r.top*2)/2,Math.round(r.width)]}).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
 const txt=[...document.querySelectorAll('#cands .cand .cpt,#cands .cand .cn,#cands .cand .cs')].filter(vis).map(e=>e.textContent.slice(0,20));
 return {ims,txt}; }"""
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
async def chart(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return k
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
  await pg.evaluate(f"()=>{{const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch==='{k}'); b&&b.click()}}"); await pg.wait_for_timeout(1500)
  return await pg.evaluate("()=>window.chartMode")
async def tip(pg):
  r=await pg.evaluate("()=>{const i=[...document.querySelectorAll('#cands img')].find(i=>i.getBoundingClientRect().width>0); if(!i) return null; const q=i.getBoundingClientRect(); return [q.left+q.width/2,q.top+q.height/2]}")
  if not r: return None
  await pg.mouse.click(r[0],r[1]); await pg.wait_for_timeout(500)
  t=await pg.evaluate("()=>{const b=document.getElementById('partyBub'); return b&&b.getBoundingClientRect().width>0&&getComputedStyle(b).display!=='none'?b.textContent:''}")
  return t
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in [(390,844),(1024,768)]:
      pg=await b.new_page(viewport={'width':W,'height':H},is_mobile=W<800,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(3500)
      m=await pg.evaluate(Q); ck(len(m['ims'])==2 and len(m['txt'])==2,f"{W} map '24: icons {m['ims']} with badges {m['txt']}")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2500)
      l=await pg.evaluate(Q); ck(l['ims']==m['ims'],f"{W} list: icons {l['ims']} == map")
      for k in ['pie','bar']:
        got=await chart(pg,k); q=await pg.evaluate(Q)
        ck(got==k and q['ims']==m['ims'],f"{W} {k}: icons {q['ims']} == map")
        ck(not q['txt'],f"{W} {k}: no text by the icons {q['txt']}")
        t=await tip(pg); ck(not t,f"{W} {k}: no tooltip on an icon tap {t!r}")
      if W==390: await pg.screenshot(path="/workspace/icons-bar-390.png",timeout=120000)
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll&&window.__ySelectAll() }"); await pg.wait_for_timeout(2000)
      rv={}
      for k in ['bar','line']:
        got=await chart(pg,k); rv[k]=(got,await pg.evaluate(Q))
        if W==390: await pg.screenshot(path=f"/workspace/icons-r{k}-390.png",timeout=120000)
        t=await tip(pg); ck(not t,f"{W} '20>'24 {k}: no tooltip on an icon tap {t!r}")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2500)
      rm=await pg.evaluate(Q); ck(len(rm['ims'])==4,f"{W} '20>'24 map: icons {rm['ims']}")
      for k,(got,q) in rv.items():
        ck(got==k and q['ims']==rm['ims'],f"{W} '20>'24 {k}: icons {q['ims']} == map")
        ck(not q['txt'],f"{W} '20>'24 {k}: no text by the icons {q['txt']}")
      ck(not er,f"{W}: no page errors {er[:2]}")
      await pg.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
