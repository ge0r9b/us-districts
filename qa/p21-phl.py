import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
    await pg.wait_for_timeout(500); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(8000); await pg.screenshot(path='../shots/b1592p21-ch-390-phl-palist.png'); print(await pg.evaluate("()=>[document.body.className.slice(0,200),(document.getElementById('crumbs')||{}).innerText,document.querySelectorAll('#listView .lvrow').length,JSON.stringify(window.__laInfo()).slice(0,200)]"))
    await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(1500)
    out={}
    async def grab(tag):
      ids=await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.dataset.cid)")
      res={'ids':ids}
      for keep in ids:
        other=[i for i in ids if i!=keep]
        await pg.evaluate(f"()=>document.querySelector('#laCands .lact[data-cid={other[0]}]').click()"); await pg.wait_for_timeout(2500)
        i=await pg.evaluate("()=>window.__laInfo()"); res[keep]=[x for x in i['order'] if 'hiladelphia' in x[0] or 'Rockledge' in x[0]]
        await pg.evaluate(f"()=>document.querySelector('#laCands .lact[data-cid={other[0]}]').click()"); await pg.wait_for_timeout(2500)
      i=await pg.evaluate("()=>window.__laInfo()"); res['tot']=[x for x in i['order'] if 'hiladelphia' in x[0] or 'Rockledge' in x[0]]
      out[tag]=res; print(tag,json.dumps(res),flush=True)
    print(await pg.evaluate("()=>[...document.querySelectorAll(\"#laCands .lact\")].map(b=>b.dataset.cid)"))
    await grab("PA counties")
    xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>/Philadelphia/.test(r.innerText));const q=r.getBoundingClientRect();return [q.left+40,q.top+q.height/2]}")
    await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(6000)
    await grab('Philadelphia towns')
    json.dump(out,open('b1592p21-phl.json','w'),indent=1); await b.close()
asyncio.run(main())
