# QA-067 (real UI): geo button > type 'America' in the institution field: only real matches (United States), never the typo
# QA-088: 'USA' lists United States, not Colusa County, CA.
# look-alikes 'South Africa' or 'Amelia County'; 'Pennsylvania' still finds Pennsylvania. WebKit 390, Chromium 375, WebKit 1024x768.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400]),flush=True); (None if c else F.append(m))
ROWS="""()=>[...document.querySelectorAll('#sheet li, #orgSearch li')].filter(l=>l.offsetParent&&l.style.display!=='none'&&!l.classList.contains('orggh')).map(l=>((l.querySelector('.nm')||l).textContent||'').trim()).filter(Boolean)"""
async def main():
  async with async_playwright() as p:
    for eng,W,H in [('webkit',390,844),('chromium',375,667),('webkit',1024,768)]:
      b=await getattr(p,eng).launch(); c=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=(W<600)); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      for q,want,bad in [('America','United States',['South Africa','Amelia County, VA']),('USA','United States',['Colusa County, CA']),('Pennsylvania','Pennsylvania',[])]:
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        await pg.click('#barGeo .fsq input'); await pg.keyboard.type(q,delay=40); await pg.wait_for_timeout(1200)
        r=await pg.evaluate(ROWS)
        ck(want in r and not any(x in r for x in bad),f"{eng} {W}x{H} '{q}': shows {want}, none of {bad}",r[:12])
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      ck(not er,f"{eng} {W}: no page errors",er); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
