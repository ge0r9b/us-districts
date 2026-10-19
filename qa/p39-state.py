# QA-111: with a state picked (no district type) zoom in and measure shading
import asyncio,sys,io
from PIL import Image
from playwright.async_api import async_playwright
URL=(sys.argv[1] if len(sys.argv)>1 else "") or "https://ge0r9b.github.io/us-districts/v2/"
ENG=sys.argv[2]; W,H=map(int,sys.argv[3].split("x")); TAG=sys.argv[4] if len(sys.argv)>4 else ""
def tint(b):
  img=Image.open(io.BytesIO(b)).convert("RGB").resize((W//4,H//4)); d=list(img.getdata())
  return round(100*sum(1 for r,g,bb in d if (r-bb>40 and r>150) or (bb-r>40 and bb>150))/len(d))
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch(); ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=(W<500 and ENG=="chromium"))
    pg=await ctx.new_page(); await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(7000)
    for yi,yr in [(2,"24"),(1,"20"),(0,"16")]:
      await pg.evaluate("i=>{window.__ySetYr(i);return 0}",yi); await pg.wait_for_timeout(1500)
      for st,(la,lo) in {"PA":(39.95,-75.16),"AZ":(33.45,-112.07)}.items():
        await pg.evaluate(f"()=>{{const s=document.getElementById('state');s.value='{st}';s.onchange();return 0}}"); await pg.wait_for_timeout(5000)
        row=[]
        for z in [6,7,8,9,10,11]:
          await pg.evaluate(f"()=>{{window.__map.setView([{la},{lo}],{z},{{animate:false}});return 0}}"); await pg.wait_for_timeout(3000)
          s=await pg.screenshot(); row.append(f"z{z}:{tint(s)}%")
          if z in (8,10): open(f"qa/shots39/{TAG}state-{ENG}-{W}x{H}-{yr}-{st}-z{z}.png","wb").write(s)
        t=await pg.evaluate("()=>[document.getElementById('state').value,window.BUILD]")
        print(yr,st,t,' '.join(row),flush=True)
    await b.close()
asyncio.run(main())
