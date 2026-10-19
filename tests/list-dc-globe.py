# QA-093: All States > tap the DC row (or a DC address search) > globe: the map view shows DC with its own numbers (title, field, thumbnails), never US totals.
# QA-098: the same for addresses outside DC (Phoenix, Tallahassee, Austin): from a list, the globe shows the precinct's title AND numbers and view, exactly as the same search from the map.
# QA-103: then a reload restores the exact selection (title, numbers, field, map colour, view), for DC and for a searched precinct.
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
XA={'wdc':"1600 Pennsylvania Ave NW, Washington, DC 20500",'phx':"1700 W Washington St, Phoenix, AZ 85007",'tlh':"400 S Monroe St, Tallahassee, FL 32399",'aus':"1100 Congress Ave, Austin, TX 78701"}
def dcnums(a):
  pc=[int(x) for x in re.findall(r'(\d+)(?:\.\d)?\s*%',a['thumbs'])]
  return any(x>=85 for x in pc) and not any(45<=x<=55 for x in pc)
HEAT="()=>{try{let n=0;map.eachLayer(l=>{if(l.options&&l.options.fillColor&&l.options.fillOpacity>0.05&&l._map)n++});return n}catch(e){return -1}}"
async def reload_ck(pg,eng,sc,er):
  a=await pg.evaluate(ST); h0=await pg.evaluate(HEAT)
  await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(400)
  sn=await pg.evaluate("()=>window.__stateSnapshot()")
  await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(11000)
  b=await pg.evaluate(ST); h1=await pg.evaluate(HEAT)
  ck(b['title']==a['title'] and b['thumbs']==a['thumbs'],f"{eng} {sc}: QA-103 reload restores the title and numbers ({b['title']!r} {b['thumbs']!r} vs {a['title']!r} {a['thumbs']!r})",[a,b,sn])
  ck(b['ph']==a['ph'],f"{eng} {sc}: QA-103 reload restores the field ({b['ph']!r} vs {a['ph']!r})",[a['ph'],b['ph']])
  ck(abs(b['z']-a['z'])<=0.5 and abs(b['c'][0]-a['c'][0])<0.02 and abs(b['c'][1]-a['c'][1])<0.02 and not b['list'],f"{eng} {sc}: QA-103 reload restores the map view (z {b['z']} {b['c']} vs {a['z']} {a['c']})",[a,b])
  ck(h1>0 and (h0<=0 or h1>=min(h0,1)),f"{eng} {sc}: QA-103 the map is coloured after the reload ({h1} filled shapes, before {h0})",[h0,h1])
async def main():
  async with async_playwright() as p:
    for eng in [e for e in ['webkit','chromium'] if not os.environ.get('ONLY') or e==os.environ['ONLY']]:
      b=await getattr(p,eng).launch(); ref=None; REF={}
      for sc in [s for s in ['back','usglobe','map-wdc','dcrow','dcaddr','map-phx','list-phx','map-tlh','list-tlh','map-aus','list-aus'] if not os.environ.get('SC') or s in os.environ['SC']]:
        c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
        await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
        tap=lambda s: pg.evaluate(CEN,s)
        if not sc.startswith('map-'):
          await pg.touchscreen.tap(*(await tap('#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await tap('li.la-row'))); await pg.wait_for_timeout(4000)
        if '-' in sc:
          await pg.touchscreen.tap(*(await tap('#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
          await pg.keyboard.type(XA[sc[-3:]],delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
          if sc.startswith('map-'):
            a=await pg.evaluate(ST); REF[sc[-3:]]=a; print('ref',sc,json.dumps(a)[:400])
            if sc=='map-wdc': ck('District of Columbia' in a['title'] and dcnums(a),f"{eng} {sc}: from the map, DC with its numbers",a)
            else: ck('Precinct' in a['title'] or 'precinct' in a['title'].lower() or re.search(r'\d',a['title']),f"{eng} {sc}: from the map, titled with the precinct",a)
            if sc=='map-phx': ck(dcnums(a) is False and re.search(r'Harris[^/]*?(6\d|7\d)%',a['thumbs']) is not None,f"{eng} {sc}: the precinct's own numbers (Harris ~70)",a)
            if not os.environ.get('NORL'): await reload_ck(pg,eng,sc,er)
            ck(not er,f"{eng} {sc}: no page errors",er); await c.close(); continue
          await pg.touchscreen.tap(*(await tap('#bGlobe'))); await pg.wait_for_timeout(3000)
          a=await pg.evaluate(ST); r=REF.get(sc[-3:])
          ck(not a['list'],f"{eng} {sc}: the globe opens the map",a)
          ck(r and a['title']==r['title'] and a['thumbs']==r['thumbs'],f"{eng} {sc}: QA-098 the globe shows the same title and numbers as the map search ({a['title']!r} {a['thumbs']!r} vs {r and (r['title'],r['thumbs'])})",[a,r])
          ck(r and abs(a['z']-r['z'])<=1 and abs(a['c'][0]-r['c'][0])<0.05 and abs(a['c'][1]-r['c'][1])<0.05,f"{eng} {sc}: QA-098 the same map view as the map search (z {a['z']} vs {r and r['z']})",[a,r])
          if not os.environ.get('NORL'): await reload_ck(pg,eng,sc,er)
          await pg.screenshot(path=f"/tmp/dcg-{eng[:2]}-{sc}.png"); ck(not er,f"{eng} {sc}: no page errors",er); await c.close(); continue
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
          if sc=='dcaddr' and REF.get('wdc'): r=REF['wdc']; ck(a['ph']==r['ph'] and abs(a['z']-r['z'])<=1,f"{eng} dcaddr: the globe opens on the address like the map search (field {a['ph']!r} z {a['z']} vs {r['ph']!r} z {r['z']})",[a,r])
          if not os.environ.get('NORL'): await reload_ck(pg,eng,sc,er)
          ck(abs(a['c'][0]-38.9)<0.3 and abs(a['c'][1]+77.03)<0.4 and a['z']>=9,f"{eng} {sc}: the map is on DC",a)
        await pg.screenshot(path=f"/tmp/dcg-{eng[:2]}-{sc}.png")
        ck(not er,f"{eng} {sc}: no page errors",er); await c.close()
      await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
