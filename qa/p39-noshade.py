# QA-111 probe: shading below state zoom with no district type
import asyncio,sys,json,io
from PIL import Image
from playwright.async_api import async_playwright
URL=(sys.argv[1] if len(sys.argv)>1 else "") or "https://ge0r9b.github.io/us-districts/v2/"
ENG=sys.argv[2] if len(sys.argv)>2 else "chromium"; W,H=map(int,(sys.argv[3] if len(sys.argv)>3 else "390x844").split("x"))
TAG=sys.argv[4] if len(sys.argv)>4 else ""; ZS=[int(z) for z in (sys.argv[5] if len(sys.argv)>5 else "5,6,7,8,9,10,11").split(",")]
YS=(sys.argv[6] if len(sys.argv)>6 else "24,20,16").split(",")
PL={"PA":(40.9,-77.7),"GA":(32.7,-83.4),"Maricopa":(33.45,-112.07),"Philly":(39.95,-75.16)}
PROBE="""()=>{const m=window.__map,P=m.getPane('natPane');let px=0,n=0;(P?[...P.querySelectorAll('canvas')]:[]).forEach(cv=>{const d=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;for(let i=3;i<d.length;i+=400){n++;if(d[i]>0)px++}});
const cs=[...document.querySelectorAll('.leaflet-pane canvas')].map(c=>c.closest('.leaflet-pane').className.replace(/leaflet-(pane|zoom-animated)/g,'').trim());
return {b:window.BUILD,z:m.getZoom(),vspan:+(window.__vspan?window.__vspan():0).toFixed(2),solid:window.__stSolid?window.__stSolid():null,nat:n?Math.round(100*px/n):null,panes:[...new Set(cs)].join('/')}}"""
def tint(img):
  img=img.resize((W//4,H//4)); t=0; a=0
  for (r,g,b) in img.getdata():
    a+=1
    if (r-b>40 and r>150) or (b-r>40 and b>150): t+=1
  return round(100*t/a)
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch(); ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=(W<500 and ENG=="chromium"))
    pg=await ctx.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:120]))
    await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(6000)
    for yr in YS:
      yi={"24":2,"20":1,"16":0}[yr]
      await pg.evaluate(f"()=>{{window.__ySetYr({yi});return 0}}"); await pg.wait_for_timeout(2500)
      for nm,(la,lo) in PL.items():
        for z in ZS:
          await pg.evaluate(f"()=>{{window.__map.setView([{la},{lo}],{z},{{animate:false}});return 0}}"); await pg.wait_for_timeout(3000)
          r=await pg.evaluate(PROBE); shot=await pg.screenshot()
          r.update(yr=yr,place=nm,tint=tint(Image.open(io.BytesIO(shot)).convert("RGB"))); print(json.dumps(r),flush=True)
          if z in (6,8,10) and nm in ("PA","Philly","Maricopa"): open(f"qa/shots39/{TAG}{ENG}-{W}x{H}-{yr}-{nm}-z{z}.png","wb").write(shot)
    print("ERRS",errs); await b.close()
asyncio.run(main())
