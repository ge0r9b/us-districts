# pass 19: QA-079 recovery: after the chart is turned off (blank screen), does the globe / reload bring the map back?
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
S=open('p19-chartoff.py').read().split('S="',1)[1].split('"\nasync def',1)[0].replace('\\\\','\\')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
    await pg.touchscreen.tap(*(await center(pg,'#chartBox .copts button[data-ch=bar]') or await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2500)
    await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
    await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2500)
    print('off',await pg.evaluate(S))
    snap=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); print('snap',snap[:300])
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(6000); print('reload',await pg.evaluate(S)); await safeshot(pg,'../shots/b1587p19-ch-390-chartoff-reload.png')
    await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000); print('globe1',await pg.evaluate(S)); await safeshot(pg,'../shots/b1587p19-ch-390-chartoff-globe1.png')
    await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000); print('globe2',await pg.evaluate(S)); await safeshot(pg,'../shots/b1587p19-ch-390-chartoff-globe2.png')
    await b.close()
asyncio.run(main())
