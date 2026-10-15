import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2]; MODE=sys.argv[3] if len(sys.argv)>3 else 'all'
JS="()=>{const og=document.getElementById('sheet'); const rows=[...og.querySelectorAll('li')].filter(l=>l.offsetParent).map(l=>(l.querySelector('.nm')||l).textContent.trim()); return {body:document.body.className.replace(/\\s+/g,' '), n:rows.length, rows:rows&&rows.slice(0,6), cnt:rows&&rows.length}}"
async def main():
  fails=0
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in((1280,800),(430,900)):
      pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      if MODE=='all': await pg.evaluate("()=>document.querySelector('#crumbs .crumb.glob').click()"); await pg.wait_for_timeout(2500)
      print(W,'entered',json.dumps(await pg.evaluate(JS)))
      inp=pg.locator('#barGeo .fsq input').first
      for q,exp in [('canada','Canada'),('Canada','Canada'),('can','Canada'),('united','United'),('colombia','Colombia'),('CANADA','Canada')]:
        await inp.fill(''); await pg.wait_for_timeout(300); await inp.type(q,delay=40); await pg.wait_for_timeout(900)
        r=await pg.evaluate(JS); ok=bool(r['rows']) and any(exp.lower() in x.lower() for x in r['rows'])
        fails+=0 if ok else 1; print(W,q,'OK' if ok else 'FAIL',r['cnt'],r['rows'][:4] if r['rows'] else None, r['body'][-40:])
      await pg.screenshot(path=f"/workspace/shots/typing-{tag}-{W}.png"); print(er[:3]); await pg.close()
    await b.close()
  print('FAILS',fails)
asyncio.run(main())
