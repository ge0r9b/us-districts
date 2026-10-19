# Re-check of older open BUGS.md headings (pass-28 era). Prints evidence per item; FAIL = still reproduces.
import asyncio,sys,json,os
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]; ENG=os.environ.get('ENG','chromium')
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+" "+json.dumps(x)[:400],flush=True); (None if c else F.append(m))
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def fresh(b,W=390,H=844):
  c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page()
  await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000); return c,pg
async def allstates(pg):
  await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await pg.evaluate(CEN,'li.la-row'))); await pg.wait_for_timeout(4000)
async def geotype(pg,q,enter=True,wait=2500):
  await pg.touchscreen.tap(*(await pg.evaluate(CEN,'#gq'))); await pg.wait_for_timeout(500); await pg.evaluate("()=>document.getElementById('gq').focus()")
  await pg.keyboard.type(q,delay=25); await pg.wait_for_timeout(wait)
  sug=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(l=>l.offsetParent&&l.closest('#gfs,.gfs,#geoFs,.sheet')).map(l=>l.innerText.replace(/\\n/g,' ').trim()).filter(Boolean).slice(0,4)")
  if enter: await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
  return sug
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch()
    # QA-016 phone first load shows both coasts
    c,pg=await fresh(b); bd=await pg.evaluate("()=>{const b=map.getBounds();return [b.getWest(),b.getEast(),b.getSouth(),b.getNorth()]}")
    ck(bd[0]<=-123.5 and bd[1]>=-70.5,"QA-016: phone first load shows WA/CA and the East Coast (map west/east)",bd)
    # QA-026 / QA-004 White House address
    await geotype(pg,"1600 Pennsylvania Ave NW, Washington, DC 20500")
    st=await pg.evaluate("()=>[document.getElementById('gq').placeholder,document.getElementById('gq').title,map.getCenter().lat,map.getCenter().lng,map.getZoom()]")
    ck(abs(st[2]-38.8977)<0.01 and abs(st[3]+77.0365)<0.01 and '20220' not in (st[0]+st[1]),"QA-004/026: Enter goes to the White House, not named 'DC 20220'",st); await c.close()
    # QA-028 ZIP
    c,pg=await fresh(b); sug=await geotype(pg,"16501",enter=True)
    st=await pg.evaluate("()=>[document.getElementById('gq').placeholder,document.getElementById('gq').title]")
    ck(any('Near ZIP 16501' in x for x in sug+st),"QA-028: ZIP shows 'Near ZIP 16501'",[sug,st]); await c.close()
    # QA-023 Pittsburgh
    c,pg=await fresh(b); sug=await geotype(pg,"Pittsburgh")
    st=await pg.evaluate("()=>[document.getElementById('gq').placeholder,(document.getElementById('crumbs')||{}).innerText]")
    ck(not any('East Pittsburgh' in (x or '') for x in st) and any('Pittsburgh' in (x or '') for x in st),"QA-023: 'Pittsburgh' + Enter goes to Pittsburgh city",[sug,st]); await c.close()
    # QA-018 tap on a row's bar drills in
    c,pg=await fresh(b); await allstates(pg)
    xy=await pg.evaluate("()=>{const n=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()==='OH');const r=n.closest('.lvrow').getBoundingClientRect();return [r.left+r.width*0.55,r.top+r.height/2]}")
    await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3500)
    nm=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow .nmx')].filter(e=>e.offsetParent).slice(0,3).map(e=>e.textContent.trim())")
    ck(not any(x in ('CA','TX','FL') for x in nm),"QA-018: tapping OH's bar drills into Ohio",nm)
    # QA-008 delta bars: no per-candidate change number inside bars
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000); await allstates(pg)
    await pg.evaluate("()=>{window.__setNum&&window.__setNum('num'); window.__ySelectAll&&window.__ySelectAll();}"); await pg.wait_for_timeout(3000)
    t=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow')].find(r=>r.offsetParent&&/^CA$/.test((r.querySelector('.nmx')||{}).textContent||''));return r?r.innerText.replace(/\\n/g,' | '):null}")
    ck(t is not None and '1.83M' not in t,"QA-008: delta CA row has no per-candidate change number in the bar",t); await c.close()
    await b.close()
  print("FAILS",len(F))
asyncio.run(main())
