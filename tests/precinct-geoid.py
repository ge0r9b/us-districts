# QA-105: census GEOID precinct names read as county + code ('Dauphin Precinct 0270'); other names unchanged.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
C=[("Pennsylvania","Dauphin County","420430270","Dauphin Precinct 0270"),("New York","Richmond County","360850061020","Richmond Precinct 0061020"),("Pennsylvania","Dauphin County","420430280","Dauphin Precinct 0280"),("Arizona","Maricopa County","242","Maricopa Precinct 242"),("Ohio","Franklin County","390491234","Franklin Precinct 1234"),("Texas","Harris County","390491234","Harris Precinct 390491234")]
async def main():
  async with async_playwright() as p:
    for eng in ['chromium','webkit']:
      b=await getattr(p,eng).launch(); pg=await b.new_page(); await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      for st,co,raw,want in C:
        g=await pg.evaluate("a=>window.precDisp(a[0],a[1],a[2])",[st,co,raw]); ok=g==want; print(("ok   " if ok else "FAIL ")+f"{eng} {st}/{raw} -> {g!r} (want {want!r})"); ok or F.append(1)
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
