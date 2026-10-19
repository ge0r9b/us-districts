# Ruling (pass 36): a mouse drag on the year knob moves the single knob like a touch drag; it never makes a range. Chromium + WebKit 1024x768.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)),flush=True); (None if c else F.append(m))
TK="i=>{const t=document.querySelector('#ysl .tk[data-i=\"'+i+'\"]').getBoundingClientRect(); return [t.left+t.width/2,t.top+t.height/2]}"
async def main():
  async with async_playwright() as p:
    for eng in ['chromium','webkit']:
      b=await getattr(p,eng).launch(); pg=await b.new_page(viewport={'width':1024,'height':768}); await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1200)
      for a,z in [(2,1),(2,0),(1,2)]:
        await pg.evaluate(f"()=>window.__ySetYr({a})"); await pg.wait_for_timeout(1200)
        x0,y=await pg.evaluate(TK,a); x1,_=await pg.evaluate(TK,z)
        await pg.mouse.move(x0,y); await pg.mouse.down(); await pg.mouse.move((x0+x1)/2,y,steps=5); await pg.mouse.move(x1,y,steps=5)
        mid=await pg.evaluate("()=>window.__ysl.get()"); await pg.mouse.up(); await pg.wait_for_timeout(1500)
        r=await pg.evaluate("()=>window.__ysl.get()")
        ck(mid[0]==mid[1] and r==[z,z],f"{eng}: mouse drag knob {a} -> {z} moves one knob (during {mid}, after {r})",[mid,r])
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
