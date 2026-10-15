# usage: python3 tests/list-all-tap.py URL tag -- tapping (touch) list-all rows selects that entity at every level; sort control hidden when no data
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
C="s=>{const e=document.querySelector(s);if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}"
async def tap(pg,sel):
  bb=await pg.evaluate(C,sel)
  if not bb: return False
  await pg.wait_for_timeout(800); bb=await pg.evaluate(C,sel); await pg.touchscreen.tap(*bb); return True
def chk(n,ok,info=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,info,flush=True)
ROW="(n)=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(x=>x.querySelector('b.rn').title===n||x.querySelector('b.rn').textContent.trim()===n); if(!r) return false; r.setAttribute('data-t','1'); return true}"
async def new(b):
  ctx=await b.new_context(viewport={"width":430,"height":800},device_scale_factor=2,has_touch=True,is_mobile=True,user_agent=UA); pg=await ctx.new_page(); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000); return pg
async def openLA(pg,menu=True):
  if menu: await tap(pg,"#bGeo"); await pg.wait_for_timeout(1200)
  await tap(pg,"li.la-row"); await pg.wait_for_timeout(3500)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    # countries: All -> list all countries -> tap several
    for name in ('Haiti','Honduras','India','Indonesia','Canada'):
      pg=await new(b)
      await pg.evaluate("()=>window.__orgGlobal()"); await pg.wait_for_timeout(1500)
      await openLA(pg,False)
      sort=await pg.evaluate("()=>getComputedStyle(document.getElementById('laSort')).display")
      if name=='Haiti': chk('countries list: sort control hidden (no data to sort)',sort=='none',sort); await pg.screenshot(path=f"/workspace/shots/lat-{tag}-countries.png")
      ok=await pg.evaluate(ROW,name); 
      if ok: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
      await pg.wait_for_timeout(2500)
      r=await pg.evaluate("()=>({w:window.__W&&window.__W(),la:window.__LA.on,ph:document.getElementById('gq').placeholder,crumb:(document.querySelector('#crumbs .crumb.cur')||{}).textContent})")
      chk(f'tap {name} selects it',ok and name in (r['ph']+' '+str(r['crumb'])),json.dumps(r)); 
      if name=='Haiti': await pg.screenshot(path=f"/workspace/shots/lat-{tag}-haiti.png")
      await pg.context.close()
    # states
    for name in ('Texas','Wyoming'):
      pg=await new(b); await openLA(pg)
      if name=='Texas': chk('states list: sort control visible',await pg.evaluate("()=>getComputedStyle(document.getElementById('laSort')).display")!='none')
      ok=await pg.evaluate(ROW,"TX" if name=='Texas' else "WY" if name=='Wyoming' else "DC")
      if ok: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
      await pg.wait_for_timeout(4000)
      r=await pg.evaluate("()=>({st:state.value||window.__v2&&0,la:window.__LA.on,ph:document.getElementById('gq').placeholder,crumb:(document.querySelector('#crumbs .crumb.cur')||{}).textContent})")
      chk(f'tap state {name}',ok and name in (str(r['crumb'])+' '+r['ph']),json.dumps(r))
      if name=='Texas': await pg.screenshot(path=f"/workspace/shots/lat-{tag}-state.png")
      await pg.context.close()
    # counties of Texas
    pg=await new(b); await pg.evaluate("()=>{ /*select Texas*/ }")
    await pg.fill("#gq","texas") if False else None
    await pg.evaluate("()=>{ const g=document.getElementById('gq'); g.focus(); }"); await pg.wait_for_timeout(500)
    await pg.keyboard.type("texas"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
    await openLA(pg)
    lab=await pg.evaluate("()=>document.querySelector('#listView .lvhead')&&document.querySelector('#listView .lvhead').textContent")
    row=await pg.evaluate("()=>{const r=document.querySelector('#listView .lvrow.la'); if(!r) return null; r.setAttribute('data-t','1'); return r.querySelector('b.rn').textContent.trim()}")
    if row: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
    await pg.wait_for_timeout(3500)
    r=await pg.evaluate("()=>({la:window.__LA.on,co:(document.getElementById('county')||{}).value,ph:document.getElementById('gq').placeholder,crumb:(document.querySelector('#crumbs .crumb.cur')||{}).textContent})")
    chk('tap county row selects it',row and row in (str(r['crumb'])+' '+r['ph']+' '+str(r['co'])),json.dumps([lab,row,r])); await pg.screenshot(path=f"/workspace/shots/lat-{tag}-county.png")
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
