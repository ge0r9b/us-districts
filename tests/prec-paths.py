# Build 1570: precinct + county tables load from v2/data (precincts2020/, precincts2024/, election2020/2024.js; 2016 from v2/data too).
# Precinct-based lists still work: PA -> Jefferson County townships have values in 2024 and 2020 (and 2016 from precincts2016),
# and the map draws PA precincts in each year (shapes always drawn).
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
SRC="()=>[...document.scripts].map(s=>s.getAttribute('src')||'').filter(s=>/precincts|election20/.test(s)).map(s=>s.split('?')[0])"
VALS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,8).map(r=>[r.querySelector('b.rn').title,[...r.querySelectorAll('[data-party]')].map(e=>e.getAttribute('data-party')).join(' / ')])"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page()
    er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(7000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/^Jefferson/.test(r.querySelector('b.rn').title)).click()"); await pg.wait_for_timeout(9000)
    v=await pg.evaluate(VALS); ck(len(v)>3 and all('Harris' in x[1] for x in v),"2024: Jefferson County townships have values",v)
    if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1000)
    await pg.evaluate("()=>{const s=document.getElementById('yslider');s.value=0;s.dispatchEvent(new Event('input',{bubbles:true}))}"); await pg.wait_for_timeout(9000)
    v=await pg.evaluate(VALS); ck(len(v)>3 and sum('Biden' in x[1] for x in v)>=3,"2020: townships have values (2020 precincts)",v)
    await pg.evaluate("()=>window.__ySet16(0)"); await pg.wait_for_timeout(9000)
    v=await pg.evaluate(VALS); ck(len(v)>3 and sum('Clinton' in x[1] for x in v)>=3,"2016: townships have values (2016 precincts)",v)
    s=await pg.evaluate(SRC); print('scripts:',s)
    ck(any(x.startswith('data/precincts2024/Pennsylvania') for x in s) and any(x.startswith('data/precincts2020/Pennsylvania') for x in s) and not any(x.startswith('../data/precincts') or x.startswith('../data/election') for x in s),"precincts 2020 / 2024 and county tables load from v2/data",s)
    ck(not er,"no page errors",er[:2]); await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
