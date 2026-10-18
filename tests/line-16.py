# build 1577: the Line chart in every range: '16>'24 = 3 points ('16, '20, '24), '16>'20 and '20>'24 = 2; never empty; Line keeps the range (QA-043); chart menu: one point = pie+bar, range = line+bar
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
PICK="""async(k)=>{const m=document.querySelector('button.rbtn.cmain');if(window.chartMode===k)return;m.click();await new Promise(r=>setTimeout(r,300));const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch===k);if(b)b.click();else if(m.dataset.ch===k)m.click()}"""
PTS="()=>{const s=document.querySelector('#cands .dlx svg'); if(!s) return -1; return [...s.querySelectorAll('circle')].filter(c=>c.getBoundingClientRect().width>0).length}"
OPTS="""async()=>{const m=document.querySelector('button.rbtn.cmain'); m.click(); await new Promise(r=>setTimeout(r,300)); const o=[m.dataset.ch,...[...document.querySelectorAll('.copts button')].map(b=>b.dataset.ch)]; document.getElementById('chartDim')&&document.getElementById('chartDim').click(); await new Promise(r=>setTimeout(r,300)); return o}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    o=await pg.evaluate(OPTS); ck(set(o)=={'pie','bar'},"single year: menu = pie + bar",o)
    for lvl,setup in [('US',None),('PA',"()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"),('Allegheny County',"()=>{const c=document.getElementById('county');c.value='Allegheny County';c.onchange&&c.onchange()}")]:
      await pg.close(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:er.append(str(e)))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      if lvl!='US': await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(7000)
      if lvl=='Allegheny County': await pg.evaluate(setup); await pg.wait_for_timeout(7000)
      for name,js,n in [("'16>'24","()=>window.__ySet16(2)",6),("'16>'20","()=>window.__ySet16(1)",4),("'20>'24","()=>{window.__ySet16(0); window.__ySelectAll()}",4)]:
        await pg.evaluate(js); await pg.wait_for_timeout(4500)
        await pg.evaluate(PICK,'line'); await pg.wait_for_timeout(2500)
        st=await pg.evaluate("()=>[window.chartMode,!!window.__y16,window.__y16hi]"); k=await pg.evaluate(PTS)
        ck(k==n,f"{lvl} {name} Line: {n//2} points per line ({k} circles)",[k,st])
        exp={"'16>'24":[True,2],"'16>'20":[True,1],"'20>'24":[False,None]}[name]
        ck(st[0]=='line' and st[1]==exp[0] and (st[2]==exp[1] if exp[0] else True),f"{lvl} {name}: Line keeps the range",st)
        if lvl=='US' and name=="'16>'24": o=await pg.evaluate(OPTS); ck(set(o)=={'line','bar'},"range: menu = line + bar, no pie",o)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(500); await pg.evaluate("()=>{const s=document.getElementById('yslider'); s.value=2; s.dispatchEvent(new Event('input',{bubbles:true}))}"); await pg.wait_for_timeout(3000)
    st=await pg.evaluate("()=>window.chartMode"); ck(st=='bar',"range -> one year with Line on: switches to bar",st)
    await pg.evaluate(PICK,'pie'); await pg.wait_for_timeout(1500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000)
    st=await pg.evaluate("()=>window.chartMode"); ck(st in ('bar','line'),"one year Pie -> range: switches to bar/line (no pie)",st)
    ck(not er,"no page errors",er[:3]); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
