# Playwright test: exact state abbreviations/names rank the state first in both filters.
import asyncio,sys
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8765/v2/"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={"width":430,"height":900})
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    SA=await pg.evaluate("window.__SA"); fails=[]
    # bottom geo filter
    await pg.click('#gq'); await pg.wait_for_timeout(800)
    for ab,nm in SA.items():
      for q in [ab,ab.lower(),nm.lower()]:
        await pg.fill('#gq',q); await pg.wait_for_timeout(250)
        f=await pg.evaluate("()=>{const l=[...document.querySelectorAll('#geofs li')].find(e=>e.offsetParent); return l?l.innerText.split('\\n')[0].trim():''}")
        exp=nm in ("Puerto Rico","Guam","U.S. Virgin Islands","American Samoa","Northern Mariana Islands")
        if not f.lower().startswith(nm.lower()) and not exp: fails.append(('geo',q,f))
    # institution filter (US level list of states)
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>{document.getElementById('bGeo').click();return 1}"); await pg.wait_for_timeout(1200)
    inp=await pg.evaluate("()=>{const a=document.activeElement; return a&&a.tagName==='INPUT'}")
    for ab,nm in SA.items():
      for q in [ab,nm]:
        await pg.keyboard.press('Control+A'); await pg.keyboard.type(q); await pg.wait_for_timeout(200)
        f=await pg.evaluate("()=>{const a=document.activeElement; const ol=a&&a.closest('.sheet,#fold,body'); const l=[...document.querySelectorAll('.sheet li, #foldList li, li')].find(e=>e.offsetParent&&e.style.display!=='none'&&!e.closest('#geofs')); return l?l.innerText.split('\\n')[0].trim():''}")
        exp=nm in ("Puerto Rico","Guam","U.S. Virgin Islands","American Samoa","Northern Mariana Islands")
        if not f.lower().startswith(nm.lower()) and not exp and not (nm=="District of Columbia" and not f): fails.append(('inst',q,f))  # DC is not in the institution state list
    # Enter goes to the state (geo filter)
    for ab,nm in [("PA","Pennsylvania"),("tx","Texas"),("DC","District of Columbia")]:
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(2500); await pg.click('#gq'); await pg.wait_for_timeout(500); await pg.fill('#gq',ab); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
      v=await pg.evaluate("()=>[state.value,document.getElementById('gq').placeholder]")
      if v[0]!=nm and not v[1].startswith(nm): fails.append(('enter',ab,v))
    print('inst input focused:',inp); print('FAILS',len(fails)); [print(x) for x in fails[:40]]
    await b.close()
asyncio.run(main())
