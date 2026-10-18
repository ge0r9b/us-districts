# district rows: flag icon at x=27 (no checkmarks), text at x=52, header rows fixed; AL senate/house + another state
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
R="()=>{const L=[...document.querySelectorAll('#sheet .foldlist li')].filter(l=>l.offsetParent); const c=l=>{const o=l.querySelector('.oic'),n=l.querySelector('.nm'); const ob=o&&o.getBoundingClientRect(); return {t:n&&n.textContent.trim(),ix:ob?Math.round(ob.left+ob.width/2):null,nx:n?Math.round(n.getBoundingClientRect().left):null,cb:[...l.querySelectorAll('input[type=checkbox]')].some(i=>i.offsetParent!==null),img:!!(o&&o.querySelector('img'))}}; const tx=e=>{ if(!e) return null; const g=document.createRange(); g.selectNodeContents(e); return Math.round(g.getBoundingClientRect().left)}; const la=document.querySelector('#sheet li.la-row .nm'), ty=document.querySelector('#barGeo .fsqlbl span'), sc=document.querySelector('#crumbs .tbScope span'); return {hx:{la:tx(la),type:tx(ty),scope:tx(sc)},n:L.length,rows:L.slice(0,4).map(c),bs:Math.round(document.getElementById('barSearch').getBoundingClientRect().top),bg:Math.round(document.getElementById('barGeo').getBoundingClientRect().top)}}"
async def run(b,tag,vp,st,kind,label):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(st.lower()); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("(k)=>document.querySelector('.lbtn[data-k='+k+']').click()",kind); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
  r=await pg.evaluate(R); rows=[x for x in r['rows'] if x['t'] and not x['t'].startswith('List all') and not x['t'].startswith(st+' ')]
  ck(f"{tag} {st} {label}: rows listed",r['n']>5 and rows,r)
  ck(f"{tag} {st} {label}: flag icon x=27, text x=52, no checkmarks",rows and all(x['img'] and abs(x['ix']-27)<=2 and abs(x['nx']-52)<=2 and not x['cb'] for x in rows),r['rows'])
  ck(f"{tag} {st} {label}: header text (state / type / List all) at x=52",all(v is not None and abs(v-52)<=2 for v in r['hx'].values()),r['hx'])
  ck(f"{tag} {st} {label}: header rows fixed",r['bs']==8 and r['bg']==64,r)
  await pg.screenshot(path=f"/workspace/shots/dm-{tag}-{st[:2]}-{kind}.png"); ck(f"{tag} {st} {label}: no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp in (("dk",{"width":1280,"height":800}),("ph",{"width":390,"height":780})):
      await run(b,tag,vp,"Alabama","senate","state senate"); await run(b,tag,vp,"Alabama","statehouse","state house"); await run(b,tag,vp,"Ohio","senate","state senate"); await run(b,tag,vp,"Mississippi","schools","school districts"); await run(b,tag,vp,"Ohio","ushouse","US House")
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
