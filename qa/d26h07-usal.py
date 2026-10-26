# Oct 26 ~7 AM (1622): US-level US House list: all at-large rows (textContent, not innerText) incl DC, and DC map position after reload of DC US House list then globe
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"../shots/b1622d26h07-{eng[:2]}-{W}x{H}-usal"
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    async def tap(sel,w=0):
      xy=await center(pg,sel); v=await tap_latency(pg,*xy); await pg.wait_for_timeout(w); return v
    await tap('#bLyr',900); await tap('#lyrRow .lbtn[data-k=ushouse]',4500)
    if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await tap('#bLyr',800)
    await tap('#bGlobe',4500)
    r=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].map(r=>r.textContent.replace(/\\s+/g,' ').trim())")
    out['n']=len(r); out['al']=[x for x in r if 'at-large' in x.lower()]; out['dc']=[x for x in r if x.startswith('DC') or 'Columbia' in x]; out['ak']=[x for x in r if x.startswith('AK')]; out['sample']=r[:3]+r[-3:]
    out['dc']=[x for x in r if x.startswith('DC') or 'Columbia' in x]; out['ak']=[x for x in r if x.startswith('AK')]; out['sample']=r[:3]+r[-3:]
    for st in ['DC','AK','WY']:
      await pg.evaluate("s=>{const e=[...document.querySelectorAll('#listView .lvrow')].find(r=>r.textContent.trim().startsWith(s));e&&e.scrollIntoView({block:'center'})}",st); await pg.wait_for_timeout(700); await safeshot(pg,f"{pre}-{st}row.png")
    # DC US House list -> reload -> globe: map position
    await tap('#bGlobe',4000); await typegq(pg,'District of Columbia'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5500)
    out['dc_map_ll']=await pg.evaluate("()=>{const m=window.__map;return [m.getZoom(),+m.getCenter().lat.toFixed(3),+m.getCenter().lng.toFixed(3)]}")
    await tap('#bGlobe',4500); out['dc_list_rows']=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].map(r=>r.innerText.replace(/\\n/g,' | '))")
    await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
    out['after_reload']=[await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText"),await pg.evaluate("()=>document.body.classList.contains('listmode')")]
    out['lat_globe']=await tap('#bGlobe',4500)
    out['dc_map_ll_after']=await pg.evaluate("()=>{const m=window.__map;return [m.getZoom(),+m.getCenter().lat.toFixed(3),+m.getCenter().lng.toFixed(3)]}")
    out['crumbs_after']=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText")
    await safeshot(pg,f"{pre}-DC-reload-globe.png")
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]
    print(json.dumps(out)[:4000]); json.dump(out,open(f"b1622d26h07-usal-{eng}-{W}x{H}.json",'w'),indent=1); await b.close()
asyncio.run(main())
