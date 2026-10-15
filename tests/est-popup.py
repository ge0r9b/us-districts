# ≈ estimate mark: popups for Alabama state senate districts say "≈ estimate" exactly when the district's data row is flagged est (tests/est-al-senate.json from ussldu.js)
import asyncio,sys,json,re,os
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
EST=json.load(open(os.path.join(os.path.dirname(__file__),"est-al-senate.json")))
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
  await pg.evaluate("()=>{ if(document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(2500)
  await pg.evaluate("()=>window.__v2.setView('map')"); await pg.wait_for_timeout(2500)
  box=await pg.evaluate("()=>{const r=document.getElementById('map').getBoundingClientRect(); return [r.left,r.top,r.width,r.height]}")
  seen={}
  for fx in (0.25,0.4,0.55,0.7):
    for fy in (0.3,0.45,0.6,0.75):
      await pg.mouse.click(box[0]+box[2]*fx,box[1]+box[3]*fy); await pg.wait_for_timeout(700)
      t=await pg.evaluate(POP)
      if t:
        m=re.search(r"AL Senate (\d+)",t)
        if m: seen[m.group(1).zfill(3)]=("≈ estimate" in t, t.replace("\n"," | "))
  print(tag,"districts seen",len(seen),sorted(seen))
  ck(tag+" popups for several districts opened",len(seen)>=3,seen)
  bad={k:v for k,v in seen.items() if v[0]!=EST.get(k)}
  ck(tag+" ≈ estimate shown exactly for estimated districts",not bad,bad)
  ck(tag+" at least one estimated district marked",any(v[0] for v in seen.values()),seen)
  ck(tag+" no page errors",not errs,errs); await pg.screenshot(path="/workspace/shots/est-%s.png"%tag); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
