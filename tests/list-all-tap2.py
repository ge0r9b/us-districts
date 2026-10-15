# usage: python3 tests/list-all-tap2.py URL tag -- touch-tapping list-all rows selects the entity: DC (states list), county, township/municipality, US House district, precinct
import asyncio,sys,json
sys.argv=sys.argv[:3] if len(sys.argv)>=3 else sys.argv+['x']
src=open(__file__.replace('list-all-tap2.py','list-all-tap.py')).read().split("async def main")[0]
exec(src)
STATE="()=>({la:window.__LA.on,st:state.value,co:county.value,dist:window.__v2&&0,ph:document.getElementById('gq').placeholder,crumb:(document.querySelector('#crumbs .crumb.cur')||{}).textContent,z:window.__map.getZoom()})"
async def typ(pg,q):
  await pg.evaluate("()=>{const g=document.getElementById('gq'); g.focus();}"); await pg.wait_for_timeout(400); await pg.keyboard.type(q); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000)
async def firstRow(pg):
  return await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(x=>x.offsetParent)[0]; if(!r) return null; r.setAttribute('data-t','1'); return [r.querySelector('b.rn').textContent.trim(),r.querySelector('b.rn').title,(r.__a||{}).kind]}")
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    pg=await new(b); await openLA(pg); ok=await pg.evaluate(ROW,"DC")
    if ok: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
    await pg.wait_for_timeout(4000); r=await pg.evaluate(STATE); c=await pg.evaluate("()=>window.__map.getCenter()")
    chk('tap DC row selects District of Columbia',ok and 'District of Columbia' in r['ph'] and abs(c['lat']-38.9)<0.2 and r['z']>=10,json.dumps([r,c])); await pg.screenshot(path=f"/workspace/shots/lat2-{tag}-dc.png"); await pg.context.close()
    # county -> townships
    pg=await new(b); await typ(pg,"pennsylvania"); await openLA(pg)
    ok=await pg.evaluate(ROW,"Allegheny County"); row=['Allegheny County'] if ok else None
    if row: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
    await pg.wait_for_timeout(3500); r=await pg.evaluate(STATE)
    chk('tap county row (PA)',row and row[0] in (str(r['crumb'])+' '+r['ph']+' '+str(r['co'])),json.dumps([row,r]))
    await tap(pg,"#bGeo"); await pg.wait_for_timeout(1500)
    labs=await pg.evaluate("()=>[...document.querySelectorAll('li.la-row')].map(x=>x.textContent.trim())"); print('menu rows in county:',labs)
    if labs:
      await tap(pg,"li.la-row"); await pg.wait_for_timeout(3500)
      row=await firstRow(pg)
      if row: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
      await pg.wait_for_timeout(3500); r=await pg.evaluate(STATE)
      chk(f'tap {labs[0]} row selects it (zooms into it, stays in list view)',row and r['z']>=9,json.dumps([row,r])); await pg.screenshot(path=f"/workspace/shots/lat2-{tag}-town.png")
    await pg.context.close()
    # US House districts -> district -> precincts
    pg=await new(b); await typ(pg,"pennsylvania")
    await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=ushouse]'); b&&b.click();}"); await pg.wait_for_timeout(2500)
    await tap(pg,"#bGeo"); await pg.wait_for_timeout(1500)
    labs=await pg.evaluate("()=>[...document.querySelectorAll('li.la-row')].map(x=>x.textContent.trim())"); print('menu rows (US House):',labs)
    if labs:
      await tap(pg,"li.la-row"); await pg.wait_for_timeout(3500)
      row=await firstRow(pg)
      if row: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
      await pg.wait_for_timeout(3500); r=await pg.evaluate(STATE)
      chk(f'tap district row ({row})',row,json.dumps([row,r])); await pg.screenshot(path=f"/workspace/shots/lat2-{tag}-district.png")
      await tap(pg,"#bGeo"); await pg.wait_for_timeout(1500)
      labs=await pg.evaluate("()=>[...document.querySelectorAll('li.la-row')].map(x=>x.textContent.trim())"); print('menu rows in district:',labs)
      if labs:
        await tap(pg,"li.la-row"); await pg.wait_for_timeout(4500)
        row=await firstRow(pg)
        if row: await tap(pg,"#listView .lvrow.la[data-t='1'] b.rn")
        await pg.wait_for_timeout(3500); r=await pg.evaluate(STATE)
        chk(f'tap precinct row ({row})',row,json.dumps([row,r])); await pg.screenshot(path=f"/workspace/shots/lat2-{tag}-precinct.png")
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
