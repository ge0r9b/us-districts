# build 1588 (user): in lists, High to low with every answer shown ranks rows by TOTAL votes cast (all candidates + other),
# in % and # mode, stacked and split bars, every year; only when ONE candidate is toggled on does it rank by that candidate
# (votes in #, share in %). A range keeps |net change| as displayed.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 and sys.argv[1].startswith("http") else "https://ge0r9b.github.io/us-districts/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
AB={"California":"CA","Florida":"FL","Texas":"TX","New York":"NY","Pennsylvania":"PA","Illinois":"IL","Ohio":"OH","Michigan":"MI"}
ab=lambda n:AB.get(n,n)
def mono(xs): return all(a>=b-1e-6 for a,b in zip(xs,xs[1:]))
async def setc(pg,k):
  if await pg.evaluate("()=>window.chartMode")==k: return
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(500)
  await pg.evaluate("k=>{const b=[...document.querySelectorAll('#chartBox button')].find(b=>b.dataset.ch===k); b&&b.click()}",k); await pg.wait_for_timeout(2500)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    info=lambda: pg.evaluate("()=>window.__laInfo()")
    async def tots(): return await pg.evaluate("()=>window.__laTots&&__laTots()")
    exp=["CA","FL","TX","NY","PA","IL","OH","MI"]; expv=[14.18,9.42,8.97,7.72,6.17,5.54,5.50,4.80]
    for yi,yr in [(0,"2016"),(1,"2020"),(2,"2024")]:
      await pg.evaluate(f"()=>window.__ySetYr({yi})"); await pg.wait_for_timeout(4000)
      for ch in ["bar","gbar"]:
        await setc(pg,ch)
        for nm in ["num","pct"]:
          await pg.evaluate(f"()=>window.__setNum('{nm}')"); await pg.wait_for_timeout(1500)
          i=await info(); o=[x for x in i['order'] if x[1] is not None]; names=[ab(x[0]) for x in o]; tag=f"{yr} {ch} {nm}"
          ck(i['sort']=='desc' and len(o)>=50 and mono([x[1] for x in o]) and o[0][1]>1e6,f"{tag}: High to low by total votes (keys are vote totals, descending)",[i['sort'],len(o),o[:4]])
          if yr=="2016": ck(names[:8]==exp and all(abs(o[k][1]/1e6-expv[k])<0.006 for k in range(8)),f"{tag}: 2016 order CA FL TX NY PA IL OH MI with 14.18M..4.80M",[[n,round(x[1]/1e6,2)] for n,x in zip(names[:8],o)])
          else: ck(names[0]=="CA",f"{tag}: CA (most votes cast) first",names[:4])
      if yr=="2016":
        await setc(pg,"bar"); await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1200)
        ids=await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.dataset.cid)")
        cl=[c for c in ids if c.startswith('h') or c.startswith('c')]; tr=[c for c in ids if c.startswith('t')]
        if cl and tr:
          await pg.evaluate(f"()=>document.querySelector('#laCands .lact[data-cid={cl[0]}]').click()"); await pg.wait_for_timeout(2000)
          i=await info(); o=[x for x in i['order'] if x[1] is not None]; names=[ab(x[0]) for x in o]
          ck(i['sort']=='desc' and names[:3]==["TX","FL","CA"] and mono([x[1] for x in o]),"2016 Trump only: High to low by Trump's votes (TX, FL, CA)",[[n,x[1]] for n,x in zip(names[:4],o)])
          await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1500); i=await info(); o=[x for x in i['order'] if x[1] is not None]
          ck(mono([x[1] for x in o]) and o[0][1]<100 and o[0][0] in ("WV","West Virginia"),"2016 Trump only, %: by Trump's share (WV first)",o[:3])
          await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(800)
          await pg.evaluate(f"()=>{{document.querySelector('#laCands .lact[data-cid={cl[0]}]').click(); document.querySelector('#laCands .lact[data-cid={tr[0]}]').click()}}"); await pg.wait_for_timeout(2000)
          i=await info(); o=[x for x in i['order'] if x[1] is not None]; names=[ab(x[0]) for x in o]
          ck(names[:3]==["CA","NY","FL"],"2016 Clinton only: High to low by Clinton's votes (CA, NY, FL)",[[n,x[1]] for n,x in zip(names[:4],o)])
          await pg.evaluate(f"()=>document.querySelector('#laCands .lact[data-cid={tr[0]}]').click()"); await pg.wait_for_timeout(2000)
          i=await info(); names=[ab(x[0]) for x in i['order'] if x[1] is not None]
          ck(names[:8]==exp,"2016 both back on: total-vote order again",names[:8])
        else: ck(False,"2016 thumbnails found",ids)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click(); window.__ySelectAll() }"); await pg.wait_for_timeout(4000)
    i=await info(); o=[x for x in i['order'] if x[1] is not None]
    ck(len(o)>=50 and mono([x[1] for x in o]),"range: High to low by |net change| as displayed",o[:4])
    ck(not er,"no page errors",er)
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
