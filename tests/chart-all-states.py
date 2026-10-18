# build 1586 (live 1585 report: PA '16 pie and bar blank): pie and bar show nonzero values for US, every state and a county in '16, '20 and '24 (Chromium sweep)
import asyncio,sys
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m, flush=True)
  if not c: fails.append(m)
P="""k=>{const p=document.querySelector('#cands > .cpanel'); if(!p) return {ok:false,why:'no panel',y:[window.__y16,window.__y16hi,window.__ymRaw&&__ymRaw()]}; const vis=e=>{const r=e.getBoundingClientRect(); return r.width>2&&r.height>2&&r.bottom>0&&r.top<innerHeight};
 if(k==='pie'){ const n=[...p.querySelectorAll('svg path, svg circle')].filter(vis).length; return {ok:n>=2&&/\\d/.test(p.textContent),n} }
 const n=[...p.querySelectorAll('.sebr .sebt i')].filter(vis).length; return {ok:n>=2&&/\\d/.test(p.textContent),n,y:[window.__y16,window.__y16hi,window.__ymRaw&&__ymRaw(),window.chartMode],h:p.innerHTML.slice(0,160)} }"""
async def setc(pg,k):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(400)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset&&b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(900)
async def yr(pg,i):
  d=await pg.evaluate("()=>[...document.querySelectorAll('#ysl .tk i')].map(i=>{const r=i.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]})")
  await pg.mouse.click(*d[i]); await pg.wait_for_timeout(1300)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844})).new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1200)
    sts=await pg.evaluate("()=>['', ...[...document.getElementById('state').options].map(o=>o.value).filter(Boolean)]")
    for st in (sts[:3] if 'quick' in sys.argv else sts)+["Pennsylvania|Allegheny County"]:
      s,c=(st.split("|")+[""])[:2]
      await pg.evaluate("([s,c])=>{const e=document.getElementById('state'); if(e.value!==s){ e.value=s; e.onchange&&e.onchange(); } if(c){ const q=document.getElementById('county'); q.value=c; q.onchange&&q.onchange(); }}",[s,c]); await pg.wait_for_timeout(2500 if s else 1200)
      bad=[]
      for i,y in [(0,"16"),(1,"20"),(2,"24")]:
        await yr(pg,i)
        for k in ["bar","pie"]:
          if await pg.evaluate("()=>window.chartMode")!=k: await setc(pg,k)
          r=await pg.evaluate(P,k)
          if not r['ok']:
            await pg.wait_for_timeout(1500); r=await pg.evaluate(P,k)
          if not r['ok']:
            bad.append((y,k,r))
            if 'dump' in sys.argv: print(await pg.evaluate("()=>({ims:[...document.querySelectorAll('#cands .cand')].map(c=>{const i=c.querySelector('img'); const r=i&&i.getBoundingClientRect(); return [c.className, r&&[Math.round(r.left),Math.round(r.top),Math.round(r.width)], getComputedStyle(c).display]}), rows:[...document.querySelectorAll('.cpanel .sebr')].map(e=>{const r=e.getBoundingClientRect(); return [e.dataset.k,Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}), pn:JSON.stringify(document.querySelector('#cands > .cpanel').getBoundingClientRect()), cands:JSON.stringify(document.getElementById('cands').getBoundingClientRect()), cls:document.getElementById('cands').className, H:innerHeight})")); await pg.screenshot(path='/workspace/fail16.png'); sys.exit(2)
      ck(not bad,f"{st or 'US'}: pie and bar drawn in '16/'20/'24 {bad}")
    ck(not er,f"no page errors {er[:2]}")
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
