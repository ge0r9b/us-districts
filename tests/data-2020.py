# build 1533: 2020 data completeness. Alaska 2020 (boroughs + House/Senate in 2024 lines, ≈), Connecticut 2020
# planning regions, area-weighted 2020 side for 2024 precincts without a same-shape 2020 precinct (≈), no gray
# 2020 legislative districts, list values equal the data files.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:500]); fails+=0 if ok else 1
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent).map(r=>({n:r.querySelector('.nmx').textContent.trim(),est:!!r.querySelector('.estm'),nd:/no\\s+(data|'\\d\\d data)/i.test(r.innerText),sg:[...r.querySelectorAll('.sg')].map(s=>s.innerText.trim()).join('|')}))"
async def setmode(pg,v):
  await pg.evaluate("v=>{const y=document.getElementById('yslider'); y.value=v; y.dispatchEvent(new Event('input',{bubbles:true}))}",v); await pg.wait_for_timeout(2500)
async def open_list(b,vp,st,kind):
  c=await b.new_context(viewport=vp); await c.add_init_script("window.__noDistTier=1"); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(st.lower()); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  if kind: await pg.evaluate("(k)=>document.querySelector('.lbtn[data-k='+k+']').click()",kind); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  return c,pg,errs
def pct(sg):
  m=re.findall(r'(\d+(?:\.\d)?)%',sg); return [float(x) for x in m]
async def run(b,tag,vp):
  # Alaska state house, 2020
  c,pg,errs=await open_list(b,vp,"Alaska","statehouse"); await setmode(pg,0)
  r=await pg.evaluate(ROWS); hd=await pg.evaluate("()=>window.__ak&&window.__ak.hd2020")
  ck(tag+" AK house 2020: 40 rows, all with values and ≈",len(r)>=40 and all(not x['nd'] and x['est'] for x in r),r[:3])
  ok=0;n=0
  for x in r:
    m=re.search(r'(\d+)',x['n']); v=hd.get(str(int(m.group(1)))) if m and hd else None; p=pct(x['sg'])
    if v and p: n+=1; ok+= any(abs(q-round(v[1]/v[2]*100,1))<0.11 for q in p)
  ck(tag+" AK house 2020: list Trump %% equals ak.js hd2020 (%d checked)"%n,n>=30 and ok==n,(n,ok))
  await setmode(pg,1); r=await pg.evaluate(ROWS)
  ck(tag+" AK house delta: change shown on every row",len(r)>=40 and all(not x['nd'] for x in r),r[:3]); ck(tag+" no page errors (AK)",not errs,errs); await c.close()
  # Alaska boroughs 2020
  c,pg,errs=await open_list(b,vp,"Alaska",None); await setmode(pg,0); r=await pg.evaluate(ROWS)
  ck(tag+" AK boroughs 2020: values on all rows, ≈ marked",len(r)>=29 and all(not x['nd'] and x['est'] for x in r),[x for x in r if x['nd'] or not x['est']][:3]); await c.close()
  # Connecticut planning regions 2020
  c,pg,errs=await open_list(b,vp,"Connecticut",None); await setmode(pg,0); r=await pg.evaluate(ROWS)
  ck(tag+" CT planning regions 2020: 9 rows with values",len(r)>=9 and all(not x['nd'] for x in r),r[:3])
  t=await pg.evaluate("()=>window.__stTot&&window.__stTot('Connecticut','2020')")
  ck(tag+" CT statewide 2020 = 1,080,831 Biden / 714,717 Trump",t and t[0]==1080831 and t[1]==714717,t); await c.close()
  # 2024 precincts get a ≈ 2020 side (Arizona)
  c=await b.new_context(viewport=vp); pg=await c.new_page(); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
  q=await pg.evaluate("""async()=>{ state.value='Arizona'; await loadPrecincts('Arizona'); await window.__v2.loadPrec20('Arizona'); const P=PREC['Arizona']||[]; const m=P.map(r=>window.__v2.match20(r)); return {n:P.length,est:m.filter(o=>o&&o.__est).length,exact:m.filter(o=>o&&!o.__est).length,none:m.filter(o=>!o).length}; }""")
  ck(tag+" AZ 2024 precincts: '20 side present for >99%% (≈ area-weighted where shapes changed) %s"%q,q['n']>1500 and q['none']<=q['n']*0.01 and q['est']>1000,q); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(m())
