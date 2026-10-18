# build 1585 (user): bar views: each bar on its thumbnail's row (centre within 3px), starts 6px right of the icon, no name text, name in a white bubble on tap, bars run under the right buttons. WebKit.
import asyncio,sys
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "http://localhost:8844/v2/"
ENG="chromium" if "chromium" in sys.argv else "webkit"
fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
G="""()=>{ const c=r=>r.top+r.height/2; const ic=[...document.querySelectorAll('#cands .cand')].map(x=>{const i=x.querySelector('img'); const r=i&&i.getBoundingClientRect(); return r&&r.width?{k:x.classList.contains('r')?'rep':'dem',cy:c(r),r:r.right,l:r.left}:null}).filter(Boolean);
 const rows=[...document.querySelectorAll('.cpanel .sebr')].map(x=>{const b=x.querySelector('.sebt').getBoundingClientRect(); const ch=x.querySelector('.sechip'); const cr=ch&&ch.getBoundingClientRect(); return {k:x.dataset.k,cy:c(b),l:b.left,rt:b.right,txt:[...x.querySelectorAll('.sebn')].map(e=>e.textContent).join(''),chip:cr?[cr.left,c(cr)]:null}});
 const rl=document.querySelector('.rail').getBoundingClientRect(); return {ic,rows,rail:rl.left,W:innerWidth}; }"""
async def chart(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
  await pg.evaluate(f"()=>{{const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch==='{k}'); b&&b.click()}}"); await pg.wait_for_timeout(1500)
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=W<800); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      for place in ["Massachusetts","Worcester County"]:
        if place=="Massachusetts": await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}")
        else: await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Worcester County';c.onchange&&c.onchange()}")
        await pg.wait_for_timeout(3500)
        if not await pg.evaluate("()=>document.body.classList.contains('listmode')"): await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2000)
        await chart(pg,'bar')
        for tb in ["closed","open"]:
          if (tb=="open")==await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
          g=await pg.evaluate(G); tag=f"{ENG} {W} {place} time {tb}"
          if W==390 and place=="Worcester County" and tb=="closed": await pg.screenshot(path="/workspace/bars-390-webkit.png" if ENG=="webkit" else "/workspace/bars-390.png",timeout=120000)
          ok=len(g['rows'])>=2 and len(g['ic'])==2
          for r in g['rows']:
            if r['k']=='oth': continue
            i=next((x for x in g['ic'] if x['k']==r['k']),None)
            ok=ok and i is not None and abs(i['cy']-r['cy'])<=3 and abs(r['l']-(i['r']+6))<=2
          ck(ok,f"{tag}: bars centred on their thumbnails and 6px right of them {[(r['k'],round(r['cy'])) for r in g['rows']]} vs {[(i['k'],round(i['cy'])) for i in g['ic']]}")
          o=next((r for r in g['rows'] if r['k']=='oth'),None)
          if o: ck(o['chip'] and abs(o['chip'][0]-g['ic'][0]['l'])<=1 and abs(o['chip'][1]-o['cy'])<=3,f"{tag}: 'Other' chip in the icon column, level with its bar {o['chip']}")
          ck(all(not r['txt'] for r in g['rows']),f"{tag}: no name text in bar rows")
          ck(max(r['rt'] for r in g['rows'])>=g['W']-10,f"{tag}: bars run to the right edge under the floating buttons ({max(r['rt'] for r in g['rows']):.0f} of {g['W']})")
        xy=await pg.evaluate("()=>{const i=document.querySelector('#cands .cand img'); const r=i.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}")
        on0=await pg.evaluate("()=>document.querySelectorAll('#cands .cand.on').length")
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(500)
        t=await pg.evaluate("()=>{const b=document.getElementById('iconBub'); return b?b.textContent:''}")
        on1=await pg.evaluate("()=>document.querySelectorAll('#cands .cand.on').length")
        ck(t in ("Kamala Harris","Donald Trump") and on1==on0,f"{ENG} {W} {place}: icon tap shows its name bubble '{t}', candidate stays on ({on0}->{on1})")
        xy=await pg.evaluate("()=>{const i=document.querySelector('.cpanel .sechip'); if(!i) return null; const r=i.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}")
        if xy:
          await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(500)
          t=await pg.evaluate("()=>{const b=document.getElementById('iconBub'); return b?b.textContent:''}"); ck(t=="Other",f"{ENG} {W} {place}: Other chip bubble '{t}'")
        await pg.wait_for_timeout(3300); t=await pg.evaluate("()=>!!document.getElementById('iconBub')"); ck(not t,f"{ENG} {W} {place}: bubble closes after 3 s")
      # range bar ('20>'24): per-party rows on the pinned icon rows
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll&&window.__ySelectAll() }"); await pg.wait_for_timeout(2000); await chart(pg,'bar'); await pg.wait_for_timeout(800)
      g=await pg.evaluate("()=>[...document.querySelectorAll('.dmx .dmr')].map(r=>{const c=x=>{const b=x.getBoundingClientRect(); return [Math.round(b.left),Math.round(b.top+b.height/2)]}; return [r.dataset.k,c(r.firstElementChild),c(r.querySelector('.dmb'))]})")
      ic=await pg.evaluate("()=>{const i=document.querySelector('#crumbs .cic').getBoundingClientRect(); return Math.round(i.left+i.width/2-15)}")
      ck(len(g)==3 and all(abs(a[1][1]-a[2][1])<=3 and abs(a[1][0]-ic)<=1 for a in g),f"{ENG} {W} range bar: each bar centred on its left icon in the icon column {g}")
      if W==390: await pg.screenshot(path="/workspace/rangebar-390-webkit.png",timeout=120000)
      xy=await pg.evaluate("()=>{const i=document.querySelector('.dmx .dmoc'); if(!i) return null; const r=i.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]}")
      if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(500)
      t=await pg.evaluate("()=>{const b=document.getElementById('iconBub'); return b?b.textContent:''}"); ck(t=="Other",f"{ENG} {W} range bar: Other chip bubble '{t}'")
      ck(not er,f"{ENG} {W}: no page errors {er[:2]}")
      await ctx.close()
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
