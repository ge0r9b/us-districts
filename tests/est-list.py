# build 1563: the ≈ prefixes the first visible in-bar value ('≈82.2%'; the net value in change mode) instead of a column after the name.
# ≈ marks on list rows: shown only where the value shown is an estimate (district rows flagged est; e24 = 2024-only estimate); gray districts filled by build 1526 are marked
import asyncio,sys,json,os
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
EST=json.load(open(os.path.join(os.path.dirname(__file__),"est-al-senate.json")))
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:400]); fails+=0 if ok else 1
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent).map(r=>({n:r.querySelector('.nmx').textContent.trim(),est:!!r.querySelector('.estm'),nd:/no\\s+(data|'\\d\\d data)/i.test(r.innerText),sg:[...r.querySelectorAll('.sg')].map(s=>s.innerText.trim()).join('|'),vis:(()=>{if(!r.querySelector('.estm')) return true; const e=r.querySelector('.estp'); if(!e||getComputedStyle(e,'::before').content.indexOf('\\u2248')<0) return false; const any=[...r.querySelectorAll('.sg b')].some(b=>b.textContent&&b.style.visibility!=='hidden'); return e.classList.contains('net')||!any||e.style.visibility!=='hidden'})()}))"
async def setmode(pg,v):
  await pg.evaluate("v=>{const y=document.getElementById('yslider'); y.value=v; y.dispatchEvent(new Event('input',{bubbles:true}))}",v); await pg.wait_for_timeout(2500)
async def open_list(b,vp,st,kind):
  c=await b.new_context(viewport=vp); await c.add_init_script("window.__noDistTier=1"); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(st.lower()); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("(k)=>document.querySelector('.lbtn[data-k='+k+']').click()",kind); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  return c,pg,errs
async def run(b,tag,vp):
  c,pg,errs=await open_list(b,vp,"Alabama","senate")
  r=await pg.evaluate(ROWS); m={x['n'].replace('District ',''):x for x in r}
  ck(tag+" AL senate 2024: ≈ exactly on estimated districts",all(m[k]['est']==EST[k] for k in EST if k in m) and len(m)>=30,[ (k,m[k]['est'],EST[k]) for k in EST if k in m and m[k]['est']!=EST[k]][:5])
  ck(tag+" ≈ prefixes the first visible in-bar value (build 1563: no separate ≈ column)",all(x['vis'] for x in r),[x for x in r if not x['vis']][:3])
  await pg.screenshot(path="/workspace/shots/el-%s-al.png"%tag); await c.close()
  c,pg,errs=await open_list(b,vp,"Mississippi","statehouse"); await pg.evaluate("()=>document.getElementById('bTime')&&document.getElementById('bTime').click()"); await pg.wait_for_timeout(500)
  g=lambda r:{x['n'].replace('District ',''):x for x in r}
  r24=g(await pg.evaluate(ROWS)); k=[x for x in ('051','054','050') if x in r24]
  ck(tag+" MS house 051/054/050 (filled 2024 gaps): value present and ≈ in 2024",bool(k) and all(r24[x]['est'] and not r24[x]['nd'] for x in k),{x:r24[x] for x in k})
  await setmode(pg,0); r20=g(await pg.evaluate(ROWS))
  ck(tag+" same districts in 2020: no ≈ (2020 is not an estimate)",bool(k) and all((not r20[x]['est']) and not r20[x]['nd'] for x in k),{x:r20[x] for x in k})
  await setmode(pg,1); rd=g(await pg.evaluate(ROWS))
  ck(tag+" same districts in delta: ≈ shown with a change value",bool(k) and all(rd[x]['est'] and not rd[x]['nd'] for x in k),{x:rd[x] for x in k})
  ck(tag+" no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
