# ≈ estimate mark: popup for an estimated district (Alabama senate 002, VEST allocation) says "≈ estimate"; an official district does not
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
POP="()=>{const p=document.querySelector('.leaflet-popup.tiny .leaflet-popup-content'); return p?p.innerText:null}"
async def run(b,tag,vp):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=senate]').click()"); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].slice(0,5).map(r=>r.innerText.replace(/\\s+/g,' ').slice(0,60))"); print(tag,rows)
  # tap the row for district 002 then look at popup text
  for nm in ("002","001"):
    await pg.evaluate("()=>window.__v2.setView('list')"); await pg.wait_for_timeout(1500)
    await pg.evaluate("(n)=>{const r=[...document.querySelectorAll('#listView .lvrow')].find(x=>x.innerText.includes('District '+n)); r&&r.click()}",nm); await pg.wait_for_timeout(2500); await pg.evaluate("()=>window.__v2.setView('map')"); await pg.wait_for_timeout(3000)
    t=await pg.evaluate(POP); print(tag,nm,repr(t))
    ck(tag+" AL senate "+nm+" popup open",bool(t),t)
    if nm=="001" and t: ck(tag+" official district has no ≈","≈" not in t,t)
    if nm=="002" and t: ck(tag+" estimated district shows ≈ estimate","≈ estimate" in t,t)
  ck(tag+" no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
