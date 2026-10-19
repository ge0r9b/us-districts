# NEW check: geo filter entry with a district type selected must show that place and clear the district type
import asyncio,sys,io
from PIL import Image
from playwright.async_api import async_playwright
URL="https://ge0r9b.github.io/us-districts/v2/"; ENG=sys.argv[1]; W,H=map(int,sys.argv[2].split("x"))
def tint(b):
  img=Image.open(io.BytesIO(b)).convert("RGB").resize((W//4,H//4)); d=list(img.getdata())
  return round(100*sum(1 for r,g,bb in d if (r-bb>40 and r>150) or (bb-r>40 and bb>150))/len(d))
INFO="""()=>({on:[...document.querySelectorAll('#lyrRow .lbtn.on')].map(b=>b.dataset.k).join(','),lbl:(document.getElementById('bLayerLbl')||{}).textContent,txt:[...document.querySelectorAll('body *')].filter(e=>e.children.length==0&&e.offsetParent&&e.getBoundingClientRect().top<120&&e.textContent.trim()).map(e=>e.textContent.trim()).slice(0,6).join(' | '),bot:[...document.querySelectorAll('body *')].filter(e=>e.children.length==0&&e.offsetParent&&e.getBoundingClientRect().top>innerHeight-70&&e.textContent.trim()).map(e=>e.textContent.trim()).join(' | ')})"""
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch()
    for q in ["Pennsylvania","Philadelphia County, PA","Pittsburgh"]:
      ctx=await b.new_context(viewport={"width":W,"height":H},has_touch=True,is_mobile=(W<500 and ENG=="chromium")); pg=await ctx.new_page()
      await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(7000)
      await pg.tap("#bLyr"); await pg.wait_for_timeout(700); await pg.tap("#lyrRow .lbtn[data-k=ushouse]"); await pg.wait_for_timeout(2500); await pg.tap("#bLyr"); await pg.wait_for_timeout(1500)
      pre=await pg.evaluate(INFO)
      await pg.tap("#bGeo"); await pg.wait_for_timeout(1300)
      ok=await pg.evaluate("()=>{const i=[...document.querySelectorAll('input')].find(i=>i.offsetParent);if(i){i.focus();return i.id||i.className}return null}")
      await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(6000)
      a=await pg.evaluate(INFO); s=await pg.screenshot(); fn=f"qa/shots39/geo-{ENG}-{W}-{q.split(',')[0].replace(' ','')}.png"; open(fn,"wb").write(s)
      print(q,"| pre on:",pre['on'],"| input",ok,"| after on:",a['on'],"| top:",a['txt'],"| bottom:",a['bot'],"| tint",tint(s),"|",fn,flush=True)
      await ctx.close()
    await b.close()
asyncio.run(main())
