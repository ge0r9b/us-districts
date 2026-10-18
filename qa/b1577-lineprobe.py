# b1577: line chart at the US map and a single state in '16>'24 (does any line plot '20?), plus the app's own state shares for NY/IL/PA/FL.
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
exec(open('b1577-retest.py').read().split('async def run(')[0].split('from common import *')[1])
async def main():
  o={}
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await gt(pg); await pg.wait_for_timeout(4000)
    o['tot']=await pg.evaluate("()=>{const o={};for(const s of ['New York','Illinois','Pennsylvania','Florida','Colorado'])for(const y of ['2016','2020','2024']){try{o[s+y]=window.__stTot(s,y)}catch(e){o[s+y]=String(e).slice(0,80)}}return o}")
    await open_time(pg); await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(8000)
    o['us_line']=await pick_chart(pg,'line'); await pg.wait_for_timeout(2000)
    o['us_page']=await pg.evaluate(PAGE); o['us_svgs']=await pg.evaluate("()=>[...document.querySelectorAll('svg polyline,svg path.ln')].filter(e=>e.getBoundingClientRect().width>40).map(e=>(e.getAttribute('points')||e.getAttribute('d')||'').slice(0,120)+' '+e.getAttribute('class')).slice(0,8)")
    await safeshot(pg,'../shots/b1577-ch-1024x768-US-16-24-line.png')
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.dispatchEvent(new Event('change',{bubbles:true}));return 1}"); await pg.wait_for_timeout(7000)
    o['pa_page']=await pg.evaluate(PAGE); o['pa_svgs']=await pg.evaluate("()=>[...document.querySelectorAll('svg polyline')].filter(e=>e.getBoundingClientRect().width>40).map(e=>e.getAttribute('points')+' '+e.getAttribute('class')).slice(0,6)")
    await safeshot(pg,'../shots/b1577-ch-1024x768-PA-16-24-line.png')
    o['err']=log['pageerr']; await c.close(); await b.close()
  json.dump(o,open('b1577-lineprobe.json','w'),indent=1); print(json.dumps(o)[:5000])
asyncio.run(main())
