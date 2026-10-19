# QA-111: pick a district type, deselect it, zoom z4..z11; then reload and repeat
import asyncio,sys,io,json
from PIL import Image
from playwright.async_api import async_playwright
URL=(sys.argv[1] if len(sys.argv)>1 else "") or "https://ge0r9b.github.io/us-districts/v2/"
ENG=sys.argv[2]; W,H=map(int,sys.argv[3].split("x")); K=sys.argv[4]; MODE=sys.argv[5]; YS=sys.argv[6].split(","); TAG=sys.argv[7] if len(sys.argv)>7 else ""
PL={"PA":(40.9,-77.7),"GA":(32.7,-83.4),"Philly":(39.95,-75.16)}
import os
if os.environ.get("ONE"): PL={"PA":(40.9,-77.7)}
def tint(b):
  img=Image.open(io.BytesIO(b)).convert("RGB").resize((W//4,H//4)); d=list(img.getdata())
  return round(100*sum(1 for r,g,bb in d if (r-bb>40 and r>150) or (bb-r>40 and bb>150))/len(d))
ST="""()=>{const T=f=>{try{return f()}catch(e){return 'E'}};const P=window.__map.getPane('natPane');return {lt:T(()=>ltype),nat:T(()=>natGroup.getLayers().length),prec:T(()=>natPrec.getLayers().length),pane:P?getComputedStyle(P).display+'/'+getComputedStyle(P).opacity:'-',solid:window.__stSolid(),body:document.body.className}}"""
async def sweep(pg,lab):
  for yr in YS:
    await pg.evaluate("i=>{if(window.__ySetYr)window.__ySetYr(i);return 0}",{"24":2,"20":1,"16":0}[yr]); await pg.wait_for_timeout(2000)
    for nm,(la,lo) in PL.items():
      await pg.evaluate(f"()=>{{window.__map.setView([{la},{lo}],4,{{animate:false}});return 0}}"); await pg.wait_for_timeout(2000); row=[]
      for z in range(4,12):
        s=await pg.screenshot(); st=await pg.evaluate(ST); row.append(f"z{z}:{tint(s)}{'S' if st['solid'] else ''}")
        if z in (6,9) : open(f"qa/shots39/desel-{TAG}{lab}-{ENG}-{W}-{K}-{MODE}-{yr}-{nm}-z{z}.png","wb").write(s)
        await pg.evaluate("()=>{window.__map.zoomIn(1);return 0}"); await pg.wait_for_timeout(2500)
      print(lab,yr,nm,' '.join(row),'| lt',st['lt'],'nat',st['nat'],'prec',st['prec'],'pane',st['pane'],flush=True)
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch(); ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=(W<500 and ENG=="chromium"))
    pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
    await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(7000)
    print("start",await pg.evaluate(ST))
    if MODE=="menu":   # open menu, tap type, tap it again (deselect), close via the type button
      await pg.tap("#bLyr"); await pg.wait_for_timeout(700)
      await pg.tap(f"#lyrRow .lbtn[data-k={K}]"); await pg.wait_for_timeout(2500)
      print("picked",await pg.evaluate(ST))
      await pg.tap(f"#lyrRow .lbtn[data-k={K}]"); await pg.wait_for_timeout(2500)
      await pg.tap("#bLyr"); await pg.wait_for_timeout(1500)
    else:              # closed-row toggle: click twice programmatically
      await pg.evaluate(f"()=>{{const b=document.querySelector('#lyrRow .lbtn[data-k={K}]');b.click();return 0}}"); await pg.wait_for_timeout(2500)
      await pg.evaluate(f"()=>{{const b=document.querySelector('#lyrRow .lbtn[data-k={K}]');b.click();return 0}}"); await pg.wait_for_timeout(2500)
    print("deselected",await pg.evaluate(ST),await pg.evaluate("()=>window.BUILD"))
    await sweep(pg,"A")
    await pg.reload(wait_until="load"); await pg.wait_for_timeout(8000); print("reloaded",await pg.evaluate(ST))
    await sweep(pg,"R")
    print("ERRS",errs); await b.close()
asyncio.run(main())
