# t210: geo filter rows use territorial-shape silhouettes, never flags (states, countries, provinces); institution filter keeps flags
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
R="()=>{const L=[...document.querySelectorAll('#geofs li')].filter(l=>l.offsetParent).slice(0,8); return L.map(l=>({t:(l.querySelector('.nm')||{}).textContent,img:!!l.querySelector('.oic img'),svg:!!l.querySelector('.oic svg path'),x:l.querySelector('.oic')?Math.round(l.querySelector('.oic').getBoundingClientRect().left+l.querySelector('.oic').getBoundingClientRect().width/2):null,nx:Math.round((l.querySelector('.nm')||l).getBoundingClientRect().left)}))}"
async def run(b,tag,vp):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(1500)
  r=await pg.evaluate(R); ck(tag+" state list: silhouettes, no flags, x=27/52",r and all(x['svg'] and not x['img'] and abs(x['x']-27)<=2 and abs(x['nx']-52)<=2 for x in r),r)
  await pg.fill("#gq","canad"); await pg.wait_for_timeout(1200); r=await pg.evaluate(R); ck(tag+" 'canad' (country + provinces): silhouettes only",r and all(x['svg'] and not x['img'] for x in r),r)
  await pg.fill("#gq","germany"); await pg.wait_for_timeout(1200); r=await pg.evaluate(R); ck(tag+" 'germany': silhouette only",r and r[0]['svg'] and not r[0]['img'],r[:2])
  await pg.screenshot(path="/workspace/shots/gi-%s.png"%tag); ck(tag+" no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
