import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
C=['Pittsburgh','Columbus','Cleveland','Portland','Portland, ME','Springfield','Springfield, MA','Boston','Kansas City','Kansas City, KS','Jackson','Richmond','Lancaster','Lancaster, PA','Austin','Burlington, VT','Warwick, RI']
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.webkit.launch(); c,pg,log=await ctx(b,390,844,True,'webkit')
    await pg.goto(URL+'?cb=1622q',wait_until='networkidle',timeout=120000); await pg.wait_for_timeout(3000)
    for q in C:
      await typegq(pg,q); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5500)
      out[q]=await pg.evaluate("()=>({crumbs:document.getElementById('crumbs').innerText.replace(/\\n/g,' > '),pop:[...document.querySelectorAll('.leaflet-popup')].map(e=>e.innerText.replace(/\\n/g,' ').slice(0,90)),c:map.getCenter(),z:map.getZoom()})")
      print(q,json.dumps(out[q]),flush=True)
    out['err']=log['pageerr']; await safeshot(pg,'shotsb1622/b1622x-q115-last.png')
    json.dump(out,open('b1622x-q115.json','w'),indent=1); await b.close()
asyncio.run(main())
