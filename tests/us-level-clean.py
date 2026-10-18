# usage: python3 tests/us-level-clean.py URL -- build 1559: at nationwide scope (no state picked) only state shapes draw.
# Drilling into several states and back to the United States must not leave sub-state (county / precinct / district-detail) paths on the
# map: the county heat layer is empty, the state-detail layer (lyrPane) holds no polygons, and the per-pane layer counts return to the
# fresh US counts — default type and US House type, 390px phone.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(m,c,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:500])); (None if c else F.append(m))
JS="""()=>{ const m=window.__map, out={}; m.eachLayer(l=>{ if(!(l instanceof L.Path)) return; const p=(l.options&&l.options.pane)||'overlayPane'; out[p]=(out[p]||0)+1; }); return {paths:out,heat:window.__heatCount?window.__heatCount():-1,st:state.value} }"""
STATES=["Arkansas","Ohio","Texas","Pennsylvania","California"]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for typ in (None,"ushouse"):
      c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000); tag=typ or "default"
      if typ: await pg.tap("#bLyr"); await pg.wait_for_timeout(700); await pg.tap("#lyrRow .lbtn[data-k=%s]"%typ); await pg.wait_for_timeout(3000)
      base=await pg.evaluate(JS)
      for st in STATES:
        await pg.evaluate("s=>{county.value=''; state.value=s; state.onchange&&state.onchange();}",st); await pg.wait_for_timeout(3500)
        await pg.evaluate("()=>{county.value=''; state.value=''; state.onchange&&state.onchange();}"); await pg.wait_for_timeout(3500)
        r=await pg.evaluate(JS)
        sub={k:v for k,v in r['paths'].items() if k in ('heatPane','lyrPane') and v>0}
        ck(f"{tag}: back at US after {st}: no sub-state paths (heat layer {r['heat']}, detail panes {sub})",r['heat']==0 and not sub,r)
        ck(f"{tag}: back at US after {st}: path counts per pane equal the fresh US map",r['paths']==base['paths'],[base['paths'],r['paths']])
      await pg.screenshot(path=f"/workspace/shots/us-level-clean-{tag}.png")
      ck(f"{tag}: no page errors",not er,er[:3]); await c.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
