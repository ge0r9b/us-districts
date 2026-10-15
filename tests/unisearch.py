# t217/t218: unisearch gives TWO rows for every entity that is both a government and a place
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
ROWS="()=>[...document.querySelectorAll('#usv li')].slice(0,12).map(l=>({nm:l.querySelector('.nm').textContent,tg:l.querySelector('.tg').textContent.trim(),img:!!l.querySelector('.oic img'),svg:!!l.querySelector('.oic svg'),star:!!l.querySelector('.oic polygon'),x:Math.round(l.querySelector('.oic').getBoundingClientRect().left+l.querySelector('.oic').getBoundingClientRect().width/2),nx:Math.round(l.querySelector('.nm').getBoundingClientRect().left),tx:Math.round(l.querySelector('.tg').getBoundingClientRect().left),nr:Math.round(l.querySelector('.nm').getBoundingClientRect().right)}))"
async def q(pg,text):
  await pg.evaluate("()=>{const i=document.getElementById('usq'); i.value=''; }")
  await pg.fill("#usq",text); await pg.wait_for_timeout(900)
  return await pg.evaluate(ROWS)
async def run(b,tag,vp):
  pg=await b.new_page(viewport=vp); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.click("#bSearch"); await pg.wait_for_timeout(2500)
  for name,exp in (("pennsylvania",("State","Pennsylvania")),("united states",("Country","United States")),("canada",("Country","Canada"))):
    r=await q(pg,name); print(tag,name,[(x['nm'],x['tg'],x['img'],x['svg'],x['star']) for x in r[:4]])
    ck(tag+" '"+name+"' has institution row "+exp[0],any(x['nm']==exp[1] and x['tg']==exp[0] and x['img'] for x in r),r[:4])
    pl=[x for x in r if x['nm']==exp[1] and x['tg']=='Place']
    ck(tag+" '"+name+"' has Place row with silhouette icon",bool(pl) and pl[0]['svg'] and not pl[0]['img'],r[:4])
    ck(tag+" '"+name+"' labels inline after the name, icons at x=27, text at x=52",all(abs(x['x']-27)<=3 and abs(x['nx']-52)<=3 and 0<=x['tx']-x['nr']<=14 for x in r[:4]),[(x['x'],x['nx'],x['tx'],x['nr']) for x in r[:4]])
  r=await q(pg,"montgomery county, pa"); print(tag,'mont',[(x['nm'],x['tg'],x['img'],x['svg'],x['star']) for x in r[:4]])
  i=[k for k,x in enumerate(r) if x['nm']=="Montgomery County, PA"]
  ck(tag+" montgomery: County row then Place row",len(i)>=2 and r[i[0]]['tg']=='County' and r[i[1]]['tg']=='Place',r[:4])
  if len(i)>=2: ck(tag+" montgomery: entity icon + star silhouette",r[i[0]]['svg'] and not r[i[0]]['star'] and r[i[1]]['svg'] and r[i[1]]['star'],r[:4])
  ck(tag+" no 'Place' label on county/town institution rows",all(x['tg']!='Place' for x in r if x['tg'] in('County','Town','Township','Borough')),r)
  ck(tag+" no 'incorporated' for states",not any('ncorporated' in x['tg'] for x in r),r)
  # picks: Place row sets geo
  r=await q(pg,"pennsylvania")
  await pg.evaluate("()=>{const l=[...document.querySelectorAll('#usv li')].find(l=>l.querySelector('.nm').textContent==='Pennsylvania'&&l.querySelector('.tg').textContent.trim()==='Place'); l.click()}"); await pg.wait_for_timeout(3000)
  s=await pg.evaluate("()=>({st:state.value,ph:document.getElementById('gq').placeholder})"); ck(tag+" Place row Pennsylvania selects Pennsylvania",s['st']=='Pennsylvania',s)
  await pg.click("#bSearch"); await pg.wait_for_timeout(2500)
  r=await q(pg,"canada")
  await pg.evaluate("()=>{const l=[...document.querySelectorAll('#usv li')].find(l=>l.querySelector('.nm').textContent==='Canada'&&l.querySelector('.tg').textContent.trim()==='Country'); l.click()}"); await pg.wait_for_timeout(3000)
  s=await pg.evaluate("()=>({w:window.__W&&window.__W(),st:state.value})"); ck(tag+" Country row Canada enters Canada",s['w']=='ca',s)
  ck(tag+" no page errors",not errs,errs)
  await pg.screenshot(path="/workspace/shots/us-%s.png"%tag); await pg.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
