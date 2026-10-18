# usage: python3 tests/field-noun.py URL -- build 1563: the top field text (entity name + mid-gray level noun, e.g. 'Pennsylvania US House districts')
# uses the full width up to one average character short of the round filter button's left edge; it ellipsizes only when it truly doesn't fit there
# (iPhone showed 'Pennsylvania sc…' with lots of room: the old cap was 100vw-120px). Same rule for the bottom geography field. 390 and 375px.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0; shots=[]
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:500]); fails+=0 if ok else 1
M="""()=>{const bs=[...document.querySelectorAll('#crumbs .crumb.cur')].filter(e=>e.getBoundingClientRect().width>0),c=bs[bs.length-1];if(!c) return null;const cs=getComputedStyle(c),cx=document.createElement('canvas').getContext('2d');cx.font=cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;const chw=cx.measureText('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ').width/52;
 const r=c.getBoundingClientRect(),bl=document.getElementById('bGeo').getBoundingClientRect().left;
 const q=document.getElementById('gq'),qr=q.getBoundingClientRect(),qs=getComputedStyle(q),gl=document.getElementById('bGlobe').getBoundingClientRect().left;cx.font=qs.fontWeight+' '+qs.fontSize+' '+qs.fontFamily;const qchw=cx.measureText('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ').width/52;
 return {t:c.textContent,noun:c.getAttribute('data-noun'),left:r.left,right:r.right,need:c.scrollWidth,have:c.clientWidth,limit:bl-chw,chw,gqRight:qr.right-parseFloat(qs.paddingRight),gqLimit:gl-qchw}}"""
async def list_of(pg,typ,word=None):
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  if typ: await pg.evaluate("k=>document.querySelector('.lbtn[data-k='+k+']').click()",typ); await pg.wait_for_timeout(3000)
  rows=await pg.evaluate("()=>[...document.querySelectorAll('li.la-row')].map(l=>l.textContent)")
  i=next((j for j,t in enumerate(rows) if word and word.lower() in t.lower()),0)
  await pg.evaluate("i=>document.querySelectorAll('li.la-row')[i].click()",i); await pg.wait_for_timeout(6000); return rows
async def run(b,W,H):
  async def fresh(st):
    c=await b.new_context(viewport={'width':W,'height':H},is_mobile=True,has_touch=True,device_scale_factor=2); pg=await c.new_page()
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    if st:
      await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type(st); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
    return c,pg
  cases=[("pennsylvania",None,"counties"),("pennsylvania","ushouse","US House"),("pennsylvania","senate","senate"),("pennsylvania","statehouse","house"),("pennsylvania","schools","school")]
  for st,typ,word in cases:
    c,pg=await fresh(st); rows=await list_of(pg,typ,word); print(' rows:',rows[:4]); m=await pg.evaluate(M)
    tag=f"{W}px {typ or 'counties'}"
    if not m: ck(tag+" crumb present",False,rows); await c.close(); continue
    full=m['t']+(' '+m['noun'] if m['noun'] else '')
    fits=m['left']+m['need']<=m['limit']+0.5
    ck(f"{tag} '{full}': text ends at most one character ({m['chw']:.1f}px) before the button (right {m['right']:.1f} <= {m['limit']:.1f})",m['right']<=m['limit']+1,m)
    ck(f"{tag} '{full}': {'fits -> not truncated' if fits else 'too long -> ellipsized at the limit'}",(m['need']<=m['have']+1) if fits else (m['need']>m['have'] and m['right']>=m['limit']-2),m)
    ck(f"{tag} bottom field: text box ends one character before the globe button ({m['gqRight']:.1f} <= {m['gqLimit']:.1f})",m['gqRight']<=m['gqLimit']+1,m)
    if W==390 and typ in ('senate','ushouse'): await pg.screenshot(path=f"/workspace/pv/noun-{typ}-{W}.png")
    await c.close()
  # drill: Susquehanna County townships
  c,pg=await fresh("pennsylvania"); await list_of(pg,None)
  await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent.startsWith('Susquehanna')).click()"); await pg.wait_for_timeout(7000)
  m=await pg.evaluate(M); full=m['t']+(' '+m['noun'] if m['noun'] else ''); fits=m['left']+m['need']<=m['limit']+0.5
  ck(f"{W}px '{full}': {'fits -> not truncated' if fits else 'ellipsized at the limit'}, within the limit",m['right']<=m['limit']+1 and ((m['need']<=m['have']+1) if fits else m['need']>m['have']),m)
  await c.close()
async def main():
  import os; os.makedirs("/workspace/pv",exist_ok=True)
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,390,844); await run(b,375,667); await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
