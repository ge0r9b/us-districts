# QA-093: All States > tap the DC row (or a DC address search) > globe: the map view shows DC with its own numbers (title, field, thumbnails), never US totals.
# QA-092: fresh load > geo > All States > globe opens the normal US view (same as the US view after Back, Back), not zoom 2 over Minnesota. WebKit + Chromium 390.
import asyncio,sys,json,re,os
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:600]),flush=True); (None if c else F.append(m))
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
CEN="s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}"
ST="""()=>({list:document.body.classList.contains('listmode'),crumbs:(document.getElementById('crumbs')||{}).innerText||'',title:[...document.querySelectorAll('#crumbs .crumb,#crumbs .tbScope,.v2title,#title')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()).join(' | '),ph:document.getElementById('gq').placeholder,val:document.getElementById('gq').value,st:state.value,
 thumbs:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,4).join(' / '),
 z:map.getZoom(),c:[+map.getCenter().lat.toFixed(2),+map.getCenter().lng.toFixed(2)]})"""
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
def dcnums(a):
  pc=[int(x) for x in re.findall(r'(\d+)(?:\.\d)?\s*%',a['thumbs'])]
  return any(x>=85 for x in pc) and not any(45<=x<=55 for x in pc)
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['webkit','chromium'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch(); ref=None
      for sc in [s for s in ['back','usglobe','dcrow','dcaddr'] if not os.environ.get('SC') or s in os.environ['SC']]:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
        tap=lambda s: pg.evaluate(CEN,s)
        await pg.touchscreen.tap(*(await tap('#bGeo'))); await pg.wait_for_timeout(1200)
        await pg.touchscreen.tap(*(await tap('li.la-row'))); await pg.wait_for_timeout(4000)
        if sc=='back':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3000)
          for i in range(2):
            xy=await tap('#bBack')
            if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(2500)
          if (await pg.evaluate(ST))['list']: await pg.touchscreen.tap(*(await tap('#bGlobe'))); await pg.wait_for_timeout(2500)
          ref=await pg.evaluate(ST); print('ref US view after Back',json.dumps(ref)[:300]); await c.close(); continue
        if sc=='dcrow':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'DC'))); await pg.wait_for_timeout(3500)
        if sc=='dcaddr':
          await pg.touchscreen.tap(*(await tap('#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
          await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(6000)
        a0=await pg.evaluate(ST)
        await pg.touchscreen.tap(*(await tap('#bGlobe'))); await pg.wait_for_timeout(3000)
        a=await pg.evaluate(ST)
        ck(not a['list'],f"{eng} {sc}: the globe opens the map",a)
        if sc=='usglobe':
          ok=ref and a['z']>=ref['z'] and abs(a['c'][0]-ref['c'][0])<1.5 and abs(a['c'][1]-ref['c'][1])<2 and a['z']>=3
          ck(bool(ok),f"{eng} QA-092: All States > globe opens the normal US view (z {a['z']} at {a['c']}; after Back,Back: {ref and (ref['z'],ref['c'])})",a)
          ck('United States' in a['title']+a['ph'],f"{eng} QA-092: still titled United States",a)
        else:
          ck(dcnums(a),f"{eng} {sc}: QA-093 the map shows DC's own numbers (Harris ~90 / Trump ~6), not US totals",{'before':a0,'after':a})
          ck('United States' not in a['title'] and ('District of Columbia' in a['title'] or 'DC' in a['title'].split()),f"{eng} {sc}: QA-093 the title says District of Columbia",a)
          tdc='District of Columbia' in a['title']; tus='United States' in a['title']
          ck((tdc and dcnums(a)) or (tus and not dcnums(a)),f"{eng} {sc}: the title matches the numbers (title {a['title']!r}, thumbs {a['thumbs']!r})",a)
          ck(abs(a['c'][0]-38.9)<0.3 and abs(a['c'][1]+77.03)<0.4 and a['z']>=9,f"{eng} {sc}: the map is on DC",a)
        await pg.screenshot(path=f"/tmp/dcg-{eng[:2]}-{sc}.png")
        ck(not er,f"{eng} {sc}: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
