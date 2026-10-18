# usage: python3 tests/institution-plural.py URL -- build 1555 institution filter: institutions only (no countries outside 'All countries'),
# flag-in-shape state icons (no silhouette), the current entity is found ('alabama' inside Alabama), plural rows 'Alabama counties' etc.
# (entity bold, noun gray) that open the bar list, county rows carry the counties icon, no stray chevron over the filter.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:600]); fails+=0 if ok else 1
ROWS="()=>[...document.querySelectorAll('#sheet li, #orgSearch li')].filter(l=>l.offsetParent).map(l=>({c:l.className,t:(l.querySelector('.nm')||l).textContent.trim(),b:(l.querySelector('.nm b')||{}).textContent||'',g:(()=>{const n=l.querySelector('.lnoun'); return n?getComputedStyle(n).color:''})(),img:(l.querySelector('.oic img')||{}).getAttribute?l.querySelector('.oic img').getAttribute('src'):'',svg:!!l.querySelector('.oic svg')}))"
async def fresh(b,vp,st=None):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); pg.__errs=[]; pg.on("pageerror",lambda e:pg.__errs.append(str(e)[:160]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3200)
  if st:
    await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type(st); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  return pg
async def typ(pg,q):
  await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input'); i.focus(); i.value='';}"); await pg.keyboard.type(q); await pg.wait_for_timeout(1300)
async def run(b,tag,vp):
  pg=await fresh(b,vp,"alabama"); await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  r=await pg.evaluate(ROWS); la=[x for x in r if 'la-row' in x['c']]
  ck(tag+" plural row reads 'Alabama counties' (entity bold, noun gray)",la and la[0]['t']=='Alabama counties' and la[0]['b']=='Alabama' and la[0]['g'] in ('rgb(142, 142, 147)',),la)
  cty=[x for x in r if x['t'].endswith('County')]
  ck(tag+" county rows carry the counties icon",len(cty)>10 and all(x['svg'] for x in cty),cty[:3])
  bb=await pg.evaluate("()=>{const b=document.getElementById('bBack'); return !!b&&b.getBoundingClientRect().width>0&&getComputedStyle(b).display!=='none'}")
  ck(tag+" no stray chevron over the filter",not bb)
  await typ(pg,"alabama"); r=await pg.evaluate(ROWS); cur=[x for x in r if 'xcur' in x['c']]; ts=[x['t'] for x in cur]
  ck(tag+" typing 'alabama' inside Alabama finds Alabama + its plural forms",ts[:2]==['Alabama','Alabama counties'] and 'Alabama US House districts' in ts and 'Alabama school districts' in ts,ts)
  ck(tag+" the Alabama row has the flag-in-shape icon",cur and 'stateflags/Alabama.png' in (cur[0]['img'] or ''),cur[:1])
  fi=await pg.evaluate("()=>{const r=document.querySelector('#barGeo .fsq .fsqrec'); return r?{h:r.innerHTML.slice(0,160),vis:r.getBoundingClientRect().width>0&&getComputedStyle(r).display!=='none'}:null}")
  ck(tag+" field icon is the flag-in-shape (no black silhouette)",fi and 'stateflags/Alabama' in fi['h'] and '<svg' not in fi['h'],fi)
  ck(tag+" no address/place rows",not any(('addr' in x['c']) or x['t'].endswith('Address') for x in r),[x for x in r if 'addr' in x['c']])
  await pg.evaluate("()=>[...document.querySelectorAll('li.xcur')].find(l=>l.dataset.k==='plural').click()"); await pg.wait_for_timeout(5000)
  i=await pg.evaluate("()=>window.__laInfo()")
  ck(tag+" 'Alabama counties' opens the bar list",i['on'] and i['lv'] and (i['lv'].get('id') if isinstance(i['lv'],dict) else i['lv'])=='counties',i)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500); await typ(pg,"alab")
  await pg.evaluate("()=>[...document.querySelectorAll('li.xcur')].find(l=>l.dataset.k==='one').click()"); await pg.wait_for_timeout(3000)
  i=await pg.evaluate("()=>window.__laInfo()"); ck(tag+" 'Alabama' row returns to the single entity (no list)",not i['on'],i)
  ck(tag+" no page errors",not pg.__errs,pg.__errs); await pg.context.close()
  # US level: institutions only, countries only under All countries
  pg=await fresh(b,vp); await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500); await typ(pg,"guat")
  r=await pg.evaluate(ROWS); ck(tag+" US level: 'guat' finds no country",not any('Guatemala' in x['t'] for x in r),[x['t'] for x in r][:8])
  await typ(pg,"ala"); r=await pg.evaluate(ROWS); ts=[x['t'] for x in r]
  ck(tag+" US level: 'ala' lists Alabama/Alaska, no countries",'Alabama' in ts and not any(x in ts for x in ('Guatemala','Malawi','Malaysia')),ts[:10])
  sa=[x for x in r if x['t'] in ('Alabama','Alaska')]; ck(tag+" state rows use flag-in-shape icons",sa and all('stateflags/' in (x['img'] or '') for x in sa),sa)
  await pg.evaluate("()=>window.__orgGlobal()"); await pg.wait_for_timeout(1800); await typ(pg,"guat")
  r=await pg.evaluate(ROWS); ck(tag+" All countries: 'guat' finds Guatemala",any('Guatemala' in x['t'] for x in r),[x['t'] for x in r][:8])
  ck(tag+" no page errors (US)",not pg.__errs,pg.__errs); await pg.context.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp in (("ph",{"width":390,"height":780}),("dk",{"width":1280,"height":800})): await run(b,tag,vp)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
