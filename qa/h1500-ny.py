# hourly 3PM (1617): QA-101 NY 2024 total and thumbnails
import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True,'chromium')
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
    await typegq(pg,'New York'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5500)
    o={'build':await pg.evaluate("window.BUILD"),'tot':await pg.evaluate("()=>window.__stTot('New York','2024')"),'th':await pg.evaluate("()=>[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' '))"),'crumbs':await pg.evaluate("()=>document.getElementById('crumbs').innerText")}
    await safeshot(pg,'shotsh1500/b1617h-ch-390x844-NY24.png'); print(json.dumps(o)); json.dump(o,open('b1617h1500-ny-chromium-390x844.json','w')); await b.close()
asyncio.run(main())
