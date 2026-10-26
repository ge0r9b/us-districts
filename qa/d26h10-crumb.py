# Oct 26 ~10 AM (1623) copy of h0300-crumb.py
# Oct 26 ~3 AM (1622): header crumb truncation probe + solo counties-drill latency
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
CR="""()=>{const c=document.getElementById('crumbs');const out={txt:c.innerText,full:c.textContent};const r=c.getBoundingClientRect();out.box=[r.left,r.top,r.right,r.bottom].map(Math.round);out.sw=c.scrollWidth;out.cw=c.clientWidth;
out.kids=[...c.querySelectorAll('*')].filter(e=>e.offsetParent&&e.children.length==0).map(e=>{const q=e.getBoundingClientRect();const s=getComputedStyle(e);return [e.textContent.slice(0,40),Math.round(q.left),Math.round(q.right),e.scrollWidth,e.clientWidth,s.textOverflow,s.maxWidth]});
const btn=[...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>{const q=b.getBoundingClientRect();return [b.id,Math.round(q.left),Math.round(q.top)]}).filter(b=>Math.abs(b[2]-r.top)<40);out.btns=btn;return out}"""
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for st,county in [s.split(':') for s in sys.argv[3].split(',')]:
      c,pg,log=await ctx(b,W,H,W<600,eng); R=out[st]={}
      async def tap(sel,wait=0):
        xy=await center(pg,sel); 
        if not xy: return None
        v=await tap_latency(pg,*xy); await pg.wait_for_timeout(wait); return v
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,st); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await tap('#bGlobe',4000); await tap('#bGeo',1200)
      R['lat_counties']=await tap('li.la-row',4500)
      xy=await pg.evaluate(NMXY,county); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMXY,county)
      R['lat_county']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000); R['c2']=await pg.evaluate(CR)
      xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent)[0];const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
      R['lat_sub']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000); R['c3']=await pg.evaluate(CR)
      await pg.screenshot(path=f"shotsb1623/d26h10-{eng[:2]}-{W}x{H}-crumb-{st}.png")
      print(st,json.dumps(R),flush=True); await c.close()
    json.dump(out,open(f'b1623d26h10-crumb-{eng}-{W}x{H}.json','w'),indent=1); await b.close()
asyncio.run(main())
