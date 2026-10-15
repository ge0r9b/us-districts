# t216u regression: climb state -> country -> all countries -> All, then All-collapse (click / type+Enter / Escape) must just close, no reselect/bounce/error
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
S="()=>({st:state.value,w:window.__W&&window.__W(),sheet:getComputedStyle(document.getElementById('sheet')).display,crumbs:[...document.querySelectorAll('#crumbs .crumb')].map(c=>c.textContent.trim()+(c.classList.contains('cur')?'*':'')).join('>'),ph:document.getElementById('gq').placeholder})"
CL="(name)=>{const c=[...document.querySelectorAll('#crumbs .crumb')].find(x=>x.textContent.trim()===name&&!x.classList.contains('cur')); if(!c) return false; c.click(); return true}"
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,d if not ok else ''); fails+=0 if ok else 1
async def climb(pg,tag):
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500)
  await pg.keyboard.type("florida"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  s=await pg.evaluate(S); ck(tag+' florida selected',s['st']=='Florida',s)
  await pg.evaluate(CL,"United States"); await pg.wait_for_timeout(2000); s=await pg.evaluate(S); ck(tag+' climb to country (filter open)',s['st']=='' and s['w']!='all' and s['sheet']=='block' and 'United States*' in s['crumbs'],s)
  await pg.evaluate(CL,"All countries"); await pg.wait_for_timeout(2000); s=await pg.evaluate(S); ck(tag+' climb to All countries/All (filter open)',s['w']=='all' and s['sheet']=='block' and s['crumbs'].startswith('All*'),s)
async def run(b,tag,vp):
  for how in ("type","esc","click-top"):
    pg=await b.new_page(viewport=vp); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await climb(pg,tag)
    if how=="type": await pg.keyboard.type("All"); await pg.keyboard.press("Enter")
    elif how=="esc": await pg.keyboard.press("Escape")
    else: await pg.evaluate("()=>{const c=document.querySelector('#crumbs .crumb.cur'); c&&c.click()}")
    await pg.wait_for_timeout(1500); s=await pg.evaluate(S)
    ck(tag+' All '+how+' just collapses (no reselect/bounce)',s['w']=='all' and s['st']=='' and s['crumbs'].startswith('All*') and s['sheet']=='none',s)
    await pg.wait_for_timeout(1500); s2=await pg.evaluate(S); ck(tag+' All '+how+' stays collapsed',s2==s,s2)
    ck(tag+' no page errors',not errs,errs)
    await pg.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780})
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
