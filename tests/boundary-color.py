# usage: python3 tests/boundary-color.py http://localhost:8765/v2/ tag  -- boundary color: white with data plotted, black with boundaries only
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,900,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      async def st(): return await pg.evaluate("()=>window.__boundShown()")
      async def probe(name,want):
        global fails
        got=await st(); ok=(got==want); fails+=0 if ok else 1; print(W,name,'shown=',got,'OK' if ok else 'FAIL'); await pg.screenshot(path=f"/workspace/shots/bound-{tag}-{t}-{name}.png")
      await probe('us-topic',True)
      await pg.evaluate("()=>{state.value='Pennsylvania';state.onchange()}"); await pg.wait_for_timeout(3500); await probe('state-topic',True)
      await pg.evaluate("()=>window.__setTopic(null)"); await pg.wait_for_timeout(1500); await probe('state-notopic',False)
      await pg.evaluate("()=>window.__setTopic('President')"); await pg.wait_for_timeout(1500); await probe('state-topic-again',True)
      await pg.evaluate("()=>{state.value='';state.onchange()}"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>window.__setTopic(null)"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{ const b=document.querySelector('#lyrRow .lbtn[data-k=senate]'); b&&b.click(); }"); await pg.wait_for_timeout(3500); await probe('districts-notopic',False)
      await pg.evaluate("()=>window.__setTopic('President')"); await pg.wait_for_timeout(2500); await probe('districts-topic',True)
      await pg.evaluate("()=>{window.__worldEnter('ca')}"); await pg.wait_for_timeout(2500); await probe('canada',False)
      print(er[:2]); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
