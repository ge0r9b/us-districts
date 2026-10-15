# t193/t206: California school districts: list-all shows; tap the field -> menu; tap top 'California' -> states; type ohio Enter -> Ohio; Escape returns
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
ST="()=>({ctx:document.body.classList.contains('ctxedit'),fs:document.body.classList.contains('foldfs'),la:document.body.classList.contains('listall'),st:state.value,n:[...document.querySelectorAll('#ctxList li')].filter(x=>x.style.display!=='none').length,top:(document.querySelector('#crumbs .tbScope')||{}).textContent,vis:[...document.querySelectorAll('#crumbs .crumb')].filter(c=>c.offsetParent&&c.getBoundingClientRect().width>0).map(c=>c.textContent.trim())})"
async def run(b,tag,vp):
  errs=[]
  async def fresh():
    c=await b.new_context(viewport=vp); pg=await c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("california"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
    await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    s=await pg.evaluate(ST); ck(tag+" CA school districts list-all showing",s['la'] and not s['fs'] and s['st']=='California',s)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(2000)
    s=await pg.evaluate(ST); ck(tag+" menu opens from list-all, only one scope crumb visible (no leak)",s['fs'] and s['vis']==['California'],s)
    await pg.evaluate("()=>document.querySelector('#crumbs .tbScope').click()"); await pg.wait_for_timeout(1000)
    return pg
  pg=await fresh(); s=await pg.evaluate(ST); ck(tag+" tap California -> state list",s['ctx'] and s['n']>=50,s)
  await pg.keyboard.type("ohio"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(5000); s=await pg.evaluate(ST); ck(tag+" type ohio + Enter -> Ohio",s['st']=='Ohio' and not s['ctx'] and s['vis']==['Ohio'],s)
  pg=await fresh(); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(tag+" Escape returns to California menu",s['st']=='California' and not s['ctx'] and s['fs'],s)
  ck(tag+" no page errors",not errs,errs)
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
