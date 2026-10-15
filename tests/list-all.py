import asyncio,sys,json
from playwright.async_api import async_playwright
W,H,tag=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
S="/workspace/shots/la2-"+tag+"-"
ST="""()=>{const LA=window.__LA; const lv=document.getElementById('listView'); const rows=[...lv.querySelectorAll('.lvrow.la')]; return {on:LA.on,n:LA.items.length,title:LA.title,bars:lv.querySelectorAll('.cbars').length,dv:lv.querySelectorAll('.dv').length,first:rows.slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | ').slice(0,90))}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
    await pg.goto("http://localhost:8765/v2/",wait_until="networkidle"); await pg.wait_for_timeout(2500)
    async def menu_row(label):
      await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
      t=await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); return l&&l.innerText}"); print('row:',t)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
    async def sh(n): await pg.screenshot(path=S+n+".png")
    # bar graph on
    await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='bar'); x&&x.click();}"); await pg.wait_for_timeout(800)
    await menu_row('us'); print('US bar',json.dumps(await pg.evaluate(ST))); await sh('us-bar')
    # sort
    print('sortbtn',await pg.evaluate("()=>{const b=document.getElementById('laSort'); const r=b&&b.getBoundingClientRect(); return b&&[b.offsetParent!==null,Math.round(r.left),Math.round(r.top)]}"))
    await pg.evaluate("()=>document.getElementById('laSort').click()"); await pg.wait_for_timeout(500); await sh('us-sortpop')
    print('pop',await pg.evaluate("()=>[...document.querySelectorAll('#laSortPop button')].map(b=>b.textContent)"))
    await pg.evaluate("()=>[...document.querySelectorAll('#laSortPop button')][1].click()"); await pg.wait_for_timeout(800)
    print('asc',json.dumps(await pg.evaluate(ST))['first'] if False else (await pg.evaluate(ST))['first']); await sh('us-asc')
    # delta
    await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
    print('delta',json.dumps(await pg.evaluate(ST))); await sh('us-delta')
    # popup on map
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2500)
    await pg.mouse.click(W*0.5,H*0.5); await pg.wait_for_timeout(1500); print('popup',await pg.evaluate("()=>{const p=document.querySelector('.leaflet-popup-content'); return p&&p.innerText.slice(0,160)}")); await sh('us-map-popup')
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1000)
    # exit by selecting a state
    await pg.evaluate("()=>{state.value='Ohio';state.onchange()}"); await pg.wait_for_timeout(2500); print('after state select on=',await pg.evaluate("()=>window.__LA.on"))
    # township -> precinct level
    await pg.evaluate("()=>{county.value='Centre County';state.value='Pennsylvania';state.onchange()}"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>{county.value='Centre County';county.onchange()}"); await pg.wait_for_timeout(3500)
    await pg.locator('#gq').click(); await pg.wait_for_timeout(600); await pg.locator('#gq').type('State College borough Centre County',delay=30); await pg.wait_for_timeout(900); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
    print('geo town ->',await pg.evaluate("()=>[document.getElementById('crumbs').innerText, state.value, county.value]"))
    await menu_row('town'); print('precincts',json.dumps(await pg.evaluate(ST)),await pg.evaluate("()=>document.getElementById('crumbs').innerText")); await sh('precinct-delta')
    await pg.evaluate("()=>window.__laExit()"); await pg.wait_for_timeout(500)
    # all countries
    await pg.evaluate("()=>{state.value='';state.onchange()}"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('#crumbs .crumb.glob').click()"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3500)
    print('countries',json.dumps(await pg.evaluate(ST))); await sh('countries')
    await b.close()
    print(er[:3])
asyncio.run(main())
