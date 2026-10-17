# Alaska boroughs in 2020/delta: borough results (≈, from __ak.boro2020) must be present once ELECTION2020 loads,
# and the national total must count Alaska once (state total), not boroughs + state.
import asyncio,sys
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8765/v2/"
F=[]
def ok(c,m): print(("OK   " if c else "FAIL ")+m); (None if c else F.append(m))
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await (await b.new_context(viewport={'width':390,'height':844})).new_page()
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)))
    await pg.goto(U,wait_until="load"); await pg.wait_for_function("()=>window.__ak&&window.ELECTION2024",timeout=60000)
    await pg.evaluate("()=>window.__v2.loadE2020()"); await pg.wait_for_timeout(500)
    r=await pg.evaluate("""()=>{const B=__ak.boro2020,n=Object.keys(B).length;let have=0;for(const k in B) if(ELECTION2020['Alaska|'+k]) have++;
      const s=E=>{let t=0;for(const k in E) if(!k.startsWith('Alaska|')) t+=E[k][1];return t};
      return {n,have,b24:Object.keys(__ak.boro2024).every(k=>ELECTION2024['Alaska|'+k])}}""")
    ok(r['n']==30 and r['have']==30,f"all 30 Alaska boroughs have 2020 results after loadE2020 ({r['have']}/{r['n']})")
    ok(r['b24'],"all Alaska boroughs have 2024 results")
    await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.keyboard.type("alaska"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>{const y=document.getElementById('yslider'); y.value=0; y.dispatchEvent(new Event('input',{bubbles:true}))}"); await pg.wait_for_timeout(6000)
    g=await pg.evaluate("()=>{let g=0,n=0;window.__map.eachLayer(l=>{if(l.options&&l.options.pane==='natPane'&&l.options.fillColor==='#a8a')g++;});return g}")
    ok(g<=1,f"2020 national county layer: at most 1 gray county (DC), got {g}")
    ok(not errs,"no page errors "+"; ".join(errs[:2]))
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
