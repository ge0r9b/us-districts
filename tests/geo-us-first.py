# build 1585 (QA-075): a US place always ranks above a foreign one of the same name: 'Georgia'+Enter = the state (the country is a lower result); same for every US/country name collision
import asyncio,sys
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"; fails=[]
def ck(c,m):
  print(("ok   " if c else "FAIL ")+m)
  if not c: fails.append(m)
async def enter(pg,q):
  await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3000)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type(q); await pg.wait_for_timeout(900)
  lst=await pg.evaluate("()=>[...document.querySelectorAll('#geofs ol li, .geofs ol li, ol li')].filter(l=>l.offsetParent).slice(0,6).map(l=>l.innerText.replace(/\\s+/g,' ').trim())")
  await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
  st=await pg.evaluate("()=>({world:document.body.classList.contains('worldmode'),state:document.getElementById('state').value,county:(document.getElementById('county')||{}).value||'',ph:document.getElementById('gq').placeholder})")
  return lst,st
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={'width':390,'height':844}); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
    lst,st=await enter(pg,"Georgia")
    ck(lst and lst[0].startswith("Georgia") and not any("Country" in x for x in lst[:1]),f"'georgia' list: the US state first {lst}")
    ck(not st['world'] and st['state']=="Georgia",f"'Georgia'+Enter goes to the state, not Tbilisi {st}")
    col=await pg.evaluate("()=>(window.COUNTRIES||[]).filter(c=>c[0]!=='us'&&window.__geoUSFirst(c[1])).map(c=>c[1])")
    print("collisions:",col)
    for q in [c for c in col if c!="Georgia"][:6]:
      lst,st=await enter(pg,q); ck(not st['world'],f"'{q}'+Enter stays in the US {st}")
    for q in ["France","Canada","Mexico"]:
      if q in col: continue
      lst,st=await enter(pg,q); ck(st['world'],f"'{q}'+Enter (no US place of that name) still goes to the country {st}")
    ck(not er,f"no page errors {er[:2]}")
    await b.close()
  print("FAILS",len(fails)); sys.exit(1 if fails else 0)
asyncio.run(main())
