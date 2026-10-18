# build 1579 (QA-046 option a): margin scale linear to +-90; Blount AL precincts shade (not one solid red); legend reads +90; US states/PA counties still read
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
REDS="""()=>{ const out=new Set(); document.querySelectorAll('.leaflet-pane canvas').forEach(cv=>{ try{ const g=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data; for(let i=0;i<g.length;i+=4*17){ if(g[i+3]<200) continue; const r=g[i],gg=g[i+1],b=g[i+2]; if(r>80&&r>gg+40&&r>b+40) out.add((r>>3)+','+(gg>>3)+','+(b>>3)); } }catch(e){} }); return out.size; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1024,'height':768}); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    ck(await pg.evaluate("()=>[marginColor(0.6)!==marginColor(0.9), marginColor(0.9)===marginColor(1)]")==[True,True],"scale: +60 and +90 differ; darkest from +90")
    lg=await pg.evaluate("()=>[...document.querySelectorAll('.heatlbl')].map(e=>e.textContent).join('|')"); ck('+90' in lg and '+60' not in lg,"legend reads +90",lg)
    await pg.screenshot(path='/workspace/scale90-us.png')
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Alabama';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{const c=document.getElementById('county');c.value='Blount County';c.onchange&&c.onchange()}"); await pg.wait_for_timeout(9000)
    n=await pg.evaluate(REDS); ck(n>=6,f"Blount precincts: {n} distinct reds (not one solid fill)",n)
    await pg.screenshot(path='/workspace/scale90-blount.png')
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(7000)
    n=await pg.evaluate(REDS); ck(n>=6,f"PA counties: {n} distinct reds",n); await pg.screenshot(path='/workspace/scale90-pa.png')
    ck(not er,"no page errors",er[:2]); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
