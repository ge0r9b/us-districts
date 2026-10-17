# Build 1547: typed geo-field text searches nationwide even with a state/county selected; addresses resolve via Census/OSM;
# 5-digit ZIP shows a ZIP row; universal search offers address rows that drop the pin. Needs network (Census + Nominatim).
import asyncio,sys
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8765/v2/"
async def main():
  bad=[]
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=await c.new_page()
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    async def typ(q,wait=4000):
      await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.fill('#gq',''); await pg.keyboard.type(q,delay=15); await pg.wait_for_timeout(wait)
    async def go(q,wait=8000):
      await typ(q,600); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(wait)
      return await pg.evaluate("()=>[state.value,county.value,(window.__v2&&0)||'']")
    st=lambda: pg.evaluate("()=>[state.value,county.value]")
    await go("Harris County, TX"); s0=await st(); print("scope",s0)
    if s0[0]!="Texas": bad.append("scope "+str(s0))
    await typ("33101"); r=await pg.evaluate("()=>[...document.querySelectorAll('#geofs li.addr')].map(l=>l.innerText)"); print("zip rows",r)
    if not any("33101" in x for x in r): bad.append("no ZIP row")
    await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
    for q,want in [("Travis County, TX",("Texas","Travis")),("Fulton County, GA",("Georgia","Fulton")),("Miami, FL",("Florida",None))]:
      await go("Harris County, TX",6000); s=await go(q); print(q,"->",s)
      if s[0]!=want[0] or (want[1] and want[1] not in s[1]): bad.append(q+" "+str(s))
    for q,want in [("3001 S Congress Ave, Austin, TX 78704","Texas"),("233 S Wacker Dr, Chicago, IL 60606","Illinois"),("701 Lee St Apt 3, Des Plaines, IL 60016","Illinois")]:
      await go("Harris County, TX",6000); await typ(q,9000)
      rows=await pg.evaluate("()=>[...document.querySelectorAll('#geofs li.addr')].map(l=>l.dataset.src+':'+l.innerText.split('\\n')[0])"); print(" sugg",rows)
      if not rows: bad.append("no suggestions "+q)
      await pg.keyboard.press("Enter"); await pg.wait_for_timeout(9000); s=await st(); print(q,"->",s)
      if s[0]!=want: bad.append(q+" "+str(s))
    # universal search
    await go("Harris County, TX",6000)
    ok=await pg.evaluate("()=>{const b=document.getElementById('bSearch'); if(b){b.click(); return true} return false}")
    await pg.wait_for_timeout(800)
    has=await pg.evaluate("()=>!!document.getElementById('usq')")
    if not has: bad.append("universal search did not open")
    else:
      await pg.focus('#usq'); await pg.keyboard.type("1 W Pratt St, Baltimore MD 21201",delay=15); await pg.wait_for_timeout(9000)
      rows=await pg.evaluate("()=>[...document.querySelectorAll('#usv li.addr')].map(l=>l.innerText.replace(/\\n/g,' | '))"); print("us rows",rows)
      if not rows: bad.append("no universal address rows")
      else:
        await pg.click('#usv li.addr'); await pg.wait_for_timeout(9000); s=await st(); print("us pick ->",s)
        if s[0]!="Maryland": bad.append("us pick "+str(s))
        await pg.screenshot(path="/workspace/addr-us-pick.png")
    await b.close()
  print("FAIL" if bad else "PASS",bad)
asyncio.run(main())
