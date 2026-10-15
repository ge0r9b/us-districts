# t205: district list-all (AL senate/house, OH senate, MS schools, OH US House): rows have data in %, #, and delta; no "no data" rows; values inside segments
import asyncio,sys,re,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:420]); fails+=0 if ok else 1
ROWS="()=>{const R=[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent); return {n:R.length,nodata:R.filter(r=>/no\\s+(data|'\\d\\d data)/i.test(r.innerText)).map(r=>r.innerText.replace(/\\s+/g,' ').slice(0,50)).slice(0,5),nd:R.filter(r=>/no\\s+(data|'\\d\\d data)/i.test(r.innerText)).length,vals:R.slice(0,8).map(r=>[...r.querySelectorAll('.sg')].map(s=>s.innerText.trim()))}}"
async def run(b,tag,vp,st,kind,label):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(st.lower()); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("(k)=>document.querySelector('.lbtn[data-k='+k+']').click()",kind); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  for mode in ('pct','num'):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(2000); r=await pg.evaluate(ROWS)
    txt=[x for row in r['vals'] for x in row if x]
    ck(f"{tag} {st} {label} {mode}: rows with data, none 'no data'",r['n']>=5 and r['nd']==0 and len(txt)>=8,r)
    ck(f"{tag} {st} {label} {mode}: values inside segments",all(('%' in x) if mode=='pct' else ('%' not in x) for x in txt),r['vals'][:3])
  await pg.screenshot(path=f"/workspace/shots/ld-{tag}-{st[:2]}-{kind}.png")
  await pg.click("#bTime"); await pg.wait_for_timeout(500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3500); r=await pg.evaluate(ROWS)
  txt=[x for row in r['vals'] for x in row if x]
  ck(f"{tag} {st} {label} delta: rows show change, no 'no data'",r['n']>=5 and r['nd']==0 and len(txt)>=4 and all(re.match(r'^[+\u2212]',x) for x in txt),r)
  ck(f"{tag} {st} {label}: no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp in (("dk",{"width":1280,"height":800}),("ph",{"width":390,"height":780})):
      for st,k,l in (("Alabama","senate","senate"),("Alabama","statehouse","house"),("Ohio","senate","senate"),("Mississippi","schools","schools"),("Ohio","ushouse","US House")):
        await run(b,tag,vp,st,k,l)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
