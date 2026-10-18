# usage: python3 tests/list-all-abbr.py URL tag -- list-all states: two-letter abbreviation at x=52 = the top fields' text, no row icon on result rows (build 1551; was x=98 with the icon at 73 since 1546), full name in the title bubble; desktop + phone
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bGeo"); await pg.wait_for_timeout(1000); await pg.click("li.la-row"); await pg.wait_for_timeout(3500)
      r=await pg.evaluate("""()=>{const rows=[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent).slice(0,12); return rows.map(x=>{const i=x.querySelector('img'),n=x.querySelector('.nmx'),ir=i?i.getBoundingClientRect():{left:0,width:0},rg=document.createRange(); rg.selectNodeContents(n); const nr=rg.getBoundingClientRect(); return {txt:n.textContent.trim(),title:x.querySelector('b.rn').title,ic:Math.round(ir.left+ir.width/2),tx:Math.round(nr.left)}})}""")
      ok=len(r)>=8 and all(len(x['txt'])==2 and len(x['title'])>2 and x['ic']==0 and abs(x['tx']-52)<=2 for x in r)
      fails+=0 if ok else 1; print(t,'OK' if ok else 'FAIL',json.dumps(r[:4]),flush=True); await pg.screenshot(path=f"/workspace/shots/abbr-{tag}-{t}.png"); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
