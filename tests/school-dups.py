# QA-074: school district lists: every row's name is unique (same-name districts carry their county), no district listed twice
import asyncio,sys,json,collections
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0; ONLY=sys.argv[2:] 
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:600]); fails+=0 if ok else 1
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>({n:(r.querySelector('[title]')||{}).title||r.innerText.split('\\n')[0].trim(),t:(()=>{const e=r.querySelector('.nmx'),x=e?e.textContent:'';if(!e||!e.clientWidth||e.scrollWidth<=e.clientWidth+1)return x;return x.slice(0,Math.floor(x.length*e.clientWidth/e.scrollWidth)-1)+'…'})(),id:r.__a&&r.__a.d?String(r.__a.d[2]||r.__a.d[1]):''}))"
async def run(b,eng,st):
  c=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=2,**({"is_mobile":True,"has_touch":True} if eng=='chromium' else {})); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(st.lower()); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  R=await pg.evaluate(ROWS)
  dn=[k for k,v in collections.Counter(x['n'] for x in R).items() if v>1]
  ck(f"{eng} {st}: {len(R)} school district rows, every name unique",len(R)>=20 and not dn,dn[:12])
  if eng=='chromium':
    dt=[k for k,v in collections.Counter(x['t'] for x in R if x['t']).items() if v>1]
    print(f"INFO {eng} {st}: rows cut to the same text at 390 (design hold, not a fail): {len(dt)}",dt[:6])
  if st=='Ohio':
    e=[x['n'] for x in R if x['n'].startswith('Eastern Local School District')]
    ck(f"{eng} Ohio: the three Eastern Local rows carry their county",len(e)==3 and all('(' in x for x in e),e)
  ck(f"{eng} {st}: no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    for eng in ('webkit','chromium'):
      b=await getattr(p,eng).launch()
      for st in (ONLY or ['Ohio','Texas','California','Vermont']): await run(b,eng,st)
      await b.close()
  print('FAILS',fails)
asyncio.run(m())
