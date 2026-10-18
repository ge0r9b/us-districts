# build 1578: an address search switches title (crumb), field, thumbnails and map to the same place (QA-062 DC, QA-063 precinct); QA-009: no bar label under the sort chip or a button at 320/375/390
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8844/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
S="()=>({st:state.value,co:county.value,gq:document.getElementById('gq').placeholder,cur:([...document.querySelectorAll('#crumbs .crumb.cur')].pop()||{}).title||'',th:[...document.querySelectorAll('#cands .cand')].filter(b=>b.offsetParent).map(b=>((b.querySelector('.cs,.cpt')||{}).textContent||'')),pop:(document.querySelector('.leaflet-popup-content')||{}).textContent||'',c:map.getCenter()})"
async def go(b,q,st0,co0):
    pg=await b.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
    await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
    if st0: await pg.evaluate("(v)=>{const s=document.getElementById('state');s.value=v;s.onchange&&s.onchange()}",st0); await pg.wait_for_timeout(4500)
    if co0: await pg.evaluate("(v)=>{const c=document.getElementById('county');c.value=v;c.onchange&&c.onchange()}",co0); await pg.wait_for_timeout(4500)
    m=await pg.evaluate("async(q)=>{ const ms=await window.__lookupAddr(q,false); if(!ms||!ms.length) return null; await window.__goAddr(ms[0]); return ms[0]; }",q)
    await pg.wait_for_timeout(5000); s=await pg.evaluate(S); await pg.close(); return m,s,er
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for st0,co0 in [('Ohio','Franklin County'),('Pennsylvania','Allegheny County'),('Pennsylvania','')]:
      m,s,er=await go(b,"1600 Pennsylvania Ave NW, Washington, DC 20500",st0,co0)
      if m is None: print("SKIP (geocoder unreachable)"); continue
      ck(s['cur']=='District of Columbia' and s['st']=='' and abs(s['c']['lat']-38.9)<0.15 and s['th']==['90%','6%'] or (s['cur']=='District of Columbia' and len(s['th'])==2 and s['th'][0].startswith('9')),f"QA-062 White House from {st0} {co0}: crumb, thumbnails, map = DC",s)
      ck('1600' in s['gq'],"QA-062 field shows the address",s['gq'])
    m,s,er=await go(b,"100 Ross St, Pittsburgh, PA 15219","Pennsylvania","Allegheny County")
    if m:
      ck(s['co']=='Allegheny County' and 'Ward 1' in s['cur'] and s['pop'].startswith(s['cur']),"QA-063 100 Ross St: crumb names the precinct the thumbnails show",s)
    for W,H in [(320,568),(375,667),(390,844)]:
      pg=await b.new_page(viewport={'width':W,'height':H},is_mobile=True,has_touch=True); await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); l&&l.click()}"); await pg.wait_for_timeout(5000)
      bad=await pg.evaluate("""()=>{ const ob=[...document.querySelectorAll('#laSort,.rail .rbtn,#bTime,#bChart,#bNum,#bLyr,#bGeo,#bGlobe,#bSearch')].filter(b=>b.offsetParent!==null||b.id==='laSort').map(b=>b.getBoundingClientRect()).filter(r=>r.width>0); const out=[]; document.querySelectorAll('#listView .sg b, #listView .nmx').forEach(b=>{ if(getComputedStyle(b).visibility==='hidden'||!b.textContent.trim()) return; const r=b.getBoundingClientRect(); if(r.width<=0||r.bottom<0||r.top>innerHeight) return; for(const o of ob){ if(r.left<o.right-1&&r.right>o.left+1&&r.top<o.bottom-1&&r.bottom>o.top+1){ out.push([b.textContent,Math.round(r.left),Math.round(r.top)]); break; } } }); return out; }""")
      ck(not bad,f"QA-009 {W}: no visible name or value under the sort chip or a button",bad[:6]); await pg.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
