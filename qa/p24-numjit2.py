# pass 24: replicate flow steps (tap_latency + screenshots) and diff all visible element rects every frame from # tap for 7 s
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
DIFF="""(ms)=>new Promise(res=>{const key=e=>(e.id?'#'+e.id:'')+'.'+String(e.className).slice(0,20)+':'+(e.childElementCount?'':e.textContent.trim().slice(0,10));
const snap=()=>{const m=new Map();for(const e of document.querySelectorAll('body *')){const r=e.getBoundingClientRect();if(!r.width||!r.height||r.bottom<0||r.top>innerHeight)continue;m.set(e,[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)].join(','))}return m};
let prev=snap();const o=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const cur=snap();const ch=[];for(const [e,v] of cur){const p=prev.get(e);if(p!==v)ch.push(key(e)+' '+(p||'new')+'>'+v)}for(const [e,v] of prev)if(!cur.has(e))ch.push(key(e)+' gone');if(ch.length)o.push([Math.round(t),ch.length,ch.slice(0,6)]);prev=cur;if(t<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"""
async def main():
  eng='chromium'; W,H=390,844
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,W,H,True,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    await tap_latency(pg,*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    await tap_latency(pg,*(await center(pg,'#laSort'))); await pg.wait_for_timeout(1200)
    await tap_latency(pg,*(await center(pg,'#laSort'))); await pg.wait_for_timeout(2200)
    d=asyncio.ensure_future(pg.evaluate(DIFF,7000)); await pg.wait_for_timeout(30)
    await tap_latency(pg,*(await center(pg,'#bNum'))); await pg.wait_for_timeout(1500)
    await pg.screenshot(path='../shots/b1596p24-ch-390-numjit2-chooser.png')
    opt=await pg.evaluate("()=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()==='#'&&b.id!=='bNum');if(!b)return null;const r=b.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
    if opt: await tap_latency(pg,*opt)
    o=await d
    sh=await pg.evaluate("()=>window.__shifts")
    print('shifts',len(sh),[x['t'] for x in sh][:12])
    for t,n,ch in o: print(t,n,ch)
    await c.close(); await b.close()
asyncio.run(main())
