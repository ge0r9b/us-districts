# usage: python3 tests/geo-menu-lists.py URL -- build 1564:
# (1) in a state, the geography menu's list row follows the district type: 'Pennsylvania school districts' / 'state house districts' /
#     'state senate districts' / 'US House districts' (it offered 'Pennsylvania counties' for the first three), and it opens that list;
# (2) the bottom geography field follows the view: PA counties list -> 'Pennsylvania' (it showed the map-centre county, e.g. 'Steuben County, NY').
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:600]); fails+=0 if ok else 1
WANT={'schools':('school districts',400),'statehouse':('state house districts',200),'senate':('state senate districts',50),'ushouse':('US House districts',17)}
async def pa(b,W,H,mob):
    errs=[]; c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=mob,has_touch=True); pg=await c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(6500)
    return c,pg,errs
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,mob in ((390,844,True),(1024,576,False)):
      c,pg,errs=await pa(b,W,H,mob)
      g=await pg.evaluate("()=>({ph:document.getElementById('gq').placeholder,crumb:document.querySelector('#crumbs .crumb.cur')?.textContent,head:document.querySelector('#listView .lvhead')?.textContent})")
      ck(f"{W}: PA counties list -> bottom field 'Pennsylvania' ({g})",g['ph']=='Pennsylvania' and 'counties' in (g['head'] or ''),g)
      await pg.evaluate("()=>{map.panBy([0,-260],{animate:false})}"); await pg.wait_for_timeout(1200)
      g2=await pg.evaluate("()=>document.getElementById('gq').placeholder"); ck(f"{W}: map moved north in the list view -> still 'Pennsylvania' ({g2})",g2=='Pennsylvania',g2)
      for k,(noun,mn) in WANT.items():
        await pg.evaluate("()=>{ if(document.getElementById('lyrRow').hidden) document.getElementById('bLyr').click() }"); await pg.wait_for_timeout(700)
        await pg.evaluate("k=>{const b=document.querySelector('#lyrRow .lbtn[data-k='+k+']'); if(!b.classList.contains('on')) b.click()}",k); await pg.wait_for_timeout(2500)
        await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click() }"); await pg.wait_for_timeout(1600)
        la=await pg.evaluate("()=>{const l=document.querySelector('#sheet li.la-row'); return l&&l.offsetParent?l.textContent.trim():null}")
        ck(f"{W} {k}: menu offers 'Pennsylvania {noun}' ({la})",la=='Pennsylvania '+noun,la)
        await pg.evaluate("()=>document.querySelector('#sheet li.la-row').click()"); await pg.wait_for_timeout(6000)
        r=await pg.evaluate("()=>({n:document.querySelectorAll('#listView .lvrow.la').length,head:document.querySelector('#listView .lvhead')?.textContent,ph:document.getElementById('gq').placeholder})")
        ck(f"{W} {k}: it opens the state's {noun} list ({r['n']} rows, '{r['head']}'), bottom field '{r['ph']}'",r['n']>=mn and noun in (r['head'] or '') and r['ph']=='Pennsylvania',r)
      ck(f"{W}: no page errors",not errs,errs); await c.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
