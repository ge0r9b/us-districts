# QA-113: a geo-filter entry clears the district type and selects the entered place (exact name, current state first): title, numbers, field, map. Chromium + WebKit 390, plus reload.
import asyncio,sys,json,os,re
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400]),flush=True); (None if c else F.append(m))
ST="()=>({crumbs:(document.getElementById('crumbs')||{}).innerText||'',ph:document.getElementById('gq').placeholder,st:state.value,co:county.value,lt:window.__stateSnapshot().lt,on:[...document.querySelectorAll('#lyrRow .lbtn.on')].map(b=>b.dataset.k),thumbs:[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ')).slice(0,2).join(' / '),c:[map.getCenter().lat,map.getCenter().lng]})"
CITIES=[('Pittsburgh','Pennsylvania','Pittsburgh',(40.44,-79.99)),('Columbus','Ohio','Columbus',(39.96,-83.0)),('Cleveland','Ohio','Cleveland',(41.48,-81.68)),('Portland','Oregon','Portland',(45.52,-122.68)),('Springfield','Missouri','Springfield',(37.2,-93.29)),('Boston','Massachusetts','Boston',(42.33,-71.06)),('Kansas City','Missouri','Kansas City',(39.1,-94.58)),('Jackson','Mississippi','Jackson',(32.3,-90.2)),('Richmond','Virginia','Richmond',(37.53,-77.46)),('Lancaster','California','Lancaster',(34.7,-118.15)),('Austin','Texas','Austin',(30.3,-97.75)),('Portland, ME','Maine','Portland',(43.66,-70.26)),('Kansas City, KS','Kansas','Kansas City',(39.11,-94.75)),('Springfield, IL','Illinois','Springfield',(39.78,-89.65)),('Fulton County, GA','Georgia','Fulton',(33.79,-84.47)),('Franklin County, OH','Ohio','Franklin',(39.97,-83.01))]
async def typ(pg,q,how='enter'):
  if how=='bgeo':
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input')||document.querySelector('.fsq input'); i&&i.focus()}"); await pg.wait_for_timeout(400)
    await pg.keyboard.type(q,delay=20); await pg.wait_for_timeout(1800); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000); return
  await pg.evaluate("()=>{const g=document.getElementById('gq'); g.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); g.focus()}"); await pg.wait_for_timeout(700)
  await pg.keyboard.type(q,delay=20); await pg.wait_for_timeout(1800)
  if how=='enter': await pg.keyboard.press('Enter')
  elif how=='button': await pg.tap('#bGlobe')
  else: await pg.evaluate("()=>{const l=[...document.querySelectorAll('#gfs li, .geofs li')].filter(l=>l.offsetParent&&!l.classList.contains('addr')).sort((a,b)=>b.getBoundingClientRect().top-a.getBoundingClientRect().top)[0]; l&&l.click()}")
  await pg.wait_for_timeout(7000)
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['chromium','webkit'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch()
      for how in os.environ.get('HOW','enter,bgeo,button,row').split(','):
       for pre,q,st,word,ll in [(None,q,st,w,ll) for (q,st,w,ll) in CITIES if how in ('enter','bgeo') or q in ('Pittsburgh','Kansas City','Fulton County, GA')]:
         c=await b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
         await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(4000)
         if pre: await typ(pg,pre)
         await pg.evaluate("()=>document.getElementById('bLyr').click()"); await pg.wait_for_timeout(800)
         await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3000)
         await pg.evaluate("()=>{ if(!document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(800)
         await typ(pg,q,how); a=await pg.evaluate(ST)
         ck(a['st']==st and word in a['crumbs'],f"{eng} {how} '{q}': title is the entered place ({a['crumbs']!r}, {a['st']})",a)
         ck(word in a['ph'],f"{eng} {how} '{q}': field names it ({a['ph']!r})",a)
         ck(a['lt'] in ('none','') and not a['on'],f"{eng} {how} '{q}': district type cleared",a)
         ck(abs(a['c'][0]-ll[0])<0.35 and abs(a['c'][1]-ll[1])<0.35,f"{eng} {how} '{q}': map over it {a['c']}",a)
         await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(400)
         await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(10000); r=await pg.evaluate(ST)
         ck(r['crumbs']==a['crumbs'] and r['thumbs']==a['thumbs'] and r['lt']==a['lt'],f"{eng} {how} '{q}': reload keeps it ({r['crumbs']!r} {r['thumbs']!r} vs {a['crumbs']!r} {a['thumbs']!r})",[a,r])
         ck(not er,f"{eng} {how} '{q}': no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
