# build 1600 batch: QA-006 (no Rockledge sliver under Philadelphia County), QA-067 (no typo matches when real ones exist),
# QA-051 ('16>'20 list thumbnails labelled 2020), QA-061 (field follows a state pick after DC), QA-068 (DC address opens at the
# address, zoom 15), QA-069 (NY precinct crumb uses the readable name). WebKit 390.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c=await b.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    t=await pg.evaluate("""async()=>{ await loadState('Pennsylvania'); await window.__loadParts('Pennsylvania'); return {ph:window.__townsIn('Pennsylvania','Philadelphia County').map(t=>t[2]), mo:window.__townsIn('Pennsylvania','Montgomery County').map(t=>t[2]).filter(n=>/Rockledge/.test(n))}; }""")
    ck(t['ph']==['Philadelphia city'] and t['mo']==['Rockledge borough'],"QA-006: Philadelphia County lists only Philadelphia city; Rockledge stays in Montgomery",t)
    r=await pg.evaluate("()=>fuzzyRank([{name:'South Africa',tag:'Country'},{name:'United States of America',tag:'Country'},{name:'American Fork city, UT',tag:'City'}],'America',50).map(x=>x.name)")
    ck('South Africa' not in r and len(r)==2,"QA-067: 'America' does not list South Africa",r)
    r=await pg.evaluate("()=>fuzzyRank([{name:'South Africa',tag:'Country'}],'Afrika',50).map(x=>x.name)")
    ck(r==['South Africa'],"QA-067: a typo still finds its place when nothing else matches",r)
    r=await pg.evaluate("()=>precDisp('New York','New York County','015/75')")
    ck(r=='New York AD 75 ED 15',"QA-069: NY precinct id reads 'New York AD 75 ED 15'",r)
    await pg.evaluate("()=>window.__goDC('1600 Pennsylvania Ave NW',[38.8977,-77.0365])"); await pg.wait_for_timeout(2500)
    m=await pg.evaluate("()=>{const c=map.getCenter();return [c.lat,c.lng,map.getZoom()]}")
    ck(abs(m[0]-38.8977)<0.003 and abs(m[1]+77.0365)<0.003 and m[2]==15,"QA-068: DC address opens at the address, zoom 15",m)
    # QA-061: DC from the All States list, then pick Delaware
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent.trim()==='DC').click()"); await pg.wait_for_timeout(3000)
    ph0=await pg.evaluate("()=>document.getElementById('gq').placeholder")
    await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Delaware';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(3500)
    ph=await pg.evaluate("()=>document.getElementById('gq').placeholder")
    ck('Columbia' in ph0 and 'Columbia' not in ph and 'Delaware' in ph,"QA-061: after DC, picking Delaware puts Delaware in the bottom field",[ph0,ph])
    # QA-051
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__ySet16(1)"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
    lb=await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact')].map(b=>b.getAttribute('aria-label'))")
    ck(lb and all('2024' not in x for x in lb) and any('2020' in x for x in lb),"QA-051: '16>'20 list thumbnails are labelled 2020",lb)
    ck(not er,"no page errors",er); await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
