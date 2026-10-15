# usage: python3 tests/state-line-weight.py URL tag -- state boundary lines are ~30-40% thicker than before at county-level zoom (applied at draw), scale gently with zoom, colors unchanged; phone + desktop
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>{ window.__sw=[]; const o=CanvasRenderingContext2D.prototype.stroke; CanvasRenderingContext2D.prototype.stroke=function(){ window.__sw.push([this.lineWidth,this.strokeStyle]); return o.apply(this,arguments); }; }")
      res={}
      for z,c in((6,[33,-85]),(7,[33,-85]),(8,[33,-85])):
        await pg.evaluate("([z,c])=>{ window.__sw=[]; window.__map.setView(c,z,{animate:false}); }",[z,c]); await pg.wait_for_timeout(2500)
        res[z]=await pg.evaluate("()=>{ const w=window.__sw.map(x=>[+(+x[0]).toFixed(2),x[1]]); const m={}; w.forEach(x=>{const k=x[0]+'|'+x[1]; m[k]=(m[k]||0)+1}); return m }")
      print(t,json.dumps(res)[:600],flush=True)
      ok=all(any(abs(float(k.split('|')[0])-1.2*f)<0.06 for k in res[z]) for z,f in((6,1.32),(7,1.34),(8,1.36)))
      fails+=0 if ok else 1; print(t,'state line weight scaled 1.32-1.36x','OK' if ok else 'FAIL',flush=True)
      await pg.evaluate("([z,c])=>{ window.__map.setView(c,z,{animate:false}); }",[6,[33,-85]]); await pg.wait_for_timeout(2000)
      await pg.screenshot(path=f"/workspace/shots/sl-{tag}-{t}.png"); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
