# pass 31 (build 1610): sort chip vs first rows' bars in Miami-Dade County cities list (time row open), Chromium 390
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
CHK="""()=>{const s=document.getElementById('laSort');const c=s.getBoundingClientRect();const cb=document.querySelector('#chartBox .cmain').getBoundingClientRect();const R=x=>[Math.round(x.left),Math.round(x.top),Math.round(x.right),Math.round(x.bottom)];
const rows=[...document.querySelectorAll('#listView .lvrow.la')].slice(0,3).map(r=>{const parts=[...r.querySelectorAll('*')].filter(e=>e.childElementCount===0||e.className&&String(e.className).match(/sg|bar/)).map(e=>[String(e.className).slice(0,20),e.textContent.trim().slice(0,10),R(e.getBoundingClientRect())]).filter(p=>p[2][2]>p[2][0]);
 const hit=parts.filter(p=>Math.min(p[2][2],c.right)-Math.max(p[2][0],c.left)>1&&Math.min(p[2][3],c.bottom)-Math.max(p[2][1],c.top)>1);return {row:r.innerText.replace(/\\n/g,' | '),box:R(r.getBoundingClientRect()),hit}});
return {chip:R(c),chart:R(cb),rows,lv:R(document.getElementById('listView').getBoundingClientRect())}}"""
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for st,co in [('Florida','Miami-Dade'),('Texas','Harris')]:
      c,pg,log=await ctx(b,390,844,True,'chromium'); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
      o=out[st]={'counties':await pg.evaluate(CHK)}
      xy=await pg.evaluate(NMXY,co); await pg.wait_for_timeout(400); await pg.touchscreen.tap(*(await pg.evaluate(NMXY,co))); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(500)
      o['cities']=await pg.evaluate(CHK); await safeshot(pg,f"../shots/b{out['build'][-4:]}p33-ch-390-chip-{st}-{co}.png")
      print(st,json.dumps(o)[:3000],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b{out['build'][-4:]}p33-chip-chromium-390.json",'w'),indent=1)
asyncio.run(main())
