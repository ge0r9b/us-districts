# QA-111: realistic animated zoom from the default view (wheel at desktop / zoomIn animated), then tap-to-select state
import asyncio,sys,json,io
from PIL import Image
from playwright.async_api import async_playwright
URL=(sys.argv[1] if len(sys.argv)>1 else "") or "https://ge0r9b.github.io/us-districts/v2/"
ENG=sys.argv[2]; W,H=map(int,sys.argv[3].split("x")); TAG=sys.argv[4] if len(sys.argv)>4 else ""
YS=(sys.argv[5] if len(sys.argv)>5 else "24,20,16").split(",")
PL={"PA":(40.9,-77.7),"GA":(32.7,-83.4),"Maricopa":(33.45,-112.07),"Philly":(39.95,-75.16)}
def tint(b):
  img=Image.open(io.BytesIO(b)).convert("RGB").resize((W//4,H//4)); d=list(img.getdata())
  return round(100*sum(1 for r,g,bb in d if (r-bb>40 and r>150) or (bb-r>40 and bb>150))/len(d))
PR="""()=>{const m=window.__map;return {z:m.getZoom(),vs:+window.__vspan().toFixed(2),solid:window.__stSolid(),b:window.BUILD,lt:(document.getElementById('bLayerLbl')||{}).textContent,hdr:(document.querySelector('#vtitle')||{}).textContent}}"""
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch(); ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=(W<500 and ENG=="chromium"))
    pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
    await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(7000)
    for yr in YS:
      await pg.evaluate("i=>{window.__ySetYr(i);return 0}",{"24":2,"20":1,"16":0}[yr]); await pg.wait_for_timeout(2500)
      for nm,(la,lo) in PL.items():
        await pg.evaluate(f"()=>{{window.__map.setView([{la},{lo}],4,{{animate:false}});return 0}}"); await pg.wait_for_timeout(2500)
        row=[]
        for step in range(8):
          s=await pg.screenshot(); r=await pg.evaluate(PR); row.append(f"z{r['z']}:{tint(s)}%{'S' if r['solid'] else ''}")
          if r['z'] in (6,8,10): open(f"qa/shots39/{TAG}{ENG}-{W}x{H}-{yr}-{nm}-z{r['z']}.png","wb").write(s)
          await pg.evaluate("()=>{window.__map.zoomIn(1,{animate:true});return 0}"); await pg.wait_for_timeout(2800)
        print(yr,nm,r['b'],repr(r['lt']),' '.join(row),flush=True)
    print("ERRS",errs); await b.close()
asyncio.run(main())
