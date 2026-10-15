# usage: python3 tests/unisearch-layout.py URL tag  -- unisearch rows: icon centered x=27, text x=52
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,900,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>{state.value='Pennsylvania';state.onchange()}"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>document.getElementById('bSearch').click()"); await pg.wait_for_timeout(2500)
      await pg.locator('#usq').type('pr',delay=60); await pg.wait_for_timeout(1500)
      r=await pg.evaluate("""()=>{const rows=[...document.querySelectorAll('#usv li')].slice(0,12); const i=document.getElementById('usq'); const ir=i.getBoundingClientRect(); const pl=parseFloat(getComputedStyle(i).paddingLeft);
        return {n:document.querySelectorAll('#usv li').length,inputText:Math.round(ir.left+pl),rows:rows.map(l=>{const o=l.querySelector('.oic').getBoundingClientRect(), n=l.querySelector('.nm').getBoundingClientRect(); return [l.querySelector('.nm').textContent.slice(0,22), l.querySelector('.tg').textContent, Math.round(o.left+o.width/2), Math.round(n.left), l.querySelector('.oic').innerHTML.length>0, Math.round(l.getBoundingClientRect().height), Math.round(l.querySelector('.tg').getBoundingClientRect().left-n.right), l.querySelector('.tg').innerHTML.includes('svg')]})}}""")
      bad=[x for x in r['rows'] if x[2]!=27 or x[3]!=52 or not x[4] or x[6]>14 or x[7] is False]; ok=r['n']>0 and not bad and r['inputText']==52; fails+=0 if ok else 1
      print(W,'OK' if ok else 'FAIL',r['n'],'inputText',r['inputText'],'bad',bad[:4]); print([ (x[0],x[1]) for x in r['rows'][:8]])
      await pg.screenshot(path=f"/workspace/shots/unisearch-{tag}-{t}.png"); print(er[:2]); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
