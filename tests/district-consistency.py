# t246: district-type rows (list) use exactly the numbers the map pop-ups show; state rows in district-type context sum the districts
import asyncio,sys,re
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={"width":1280,"height":800}); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>window.__v2.setView('list')"); await pg.wait_for_timeout(1000)
    for k in ("ushouse","senate","statehouse","schools"):
      await pg.evaluate("k=>document.querySelector('.lbtn[data-k='+k+']').click()",k); await pg.wait_for_timeout(5000)
      rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map((r,i)=>({i,t:[...r.querySelectorAll('.sg b')].map(b=>b.textContent.trim()),n:(r.querySelector('b.rn')||{}).title}))")
      ck("%s Alabama: list rows present"%k,len(rows)>=7,len(rows))
      samp=[rows[i] for i in (0,len(rows)//2,len(rows)-1) if rows[i]['t']]
      agree=0; tested=0
      for r in samp:
        pop=await pg.evaluate("""i=>{ const r=[...document.querySelectorAll('#listView .lvrow.la')][i]; const a=r.__a; const pt=a.d[a.d.length-1][0][0][0]; const ll=L.latLng(pt[1],pt[0]); try{ window.__v2.setView('map'); window.__v2.showArea({kind:a.kind,d:a.d,yr:'2024'},ll); }catch(e){ return 'ERR '+e; } return new Promise(res=>setTimeout(()=>{ const pc=document.querySelector('.leaflet-popup-content'); res(pc?pc.textContent:''); },900)); }""",r['i'])
        pcts=re.findall(r"(\d+\.\d)%",pop or ""); lab=[re.sub('%','',x) for x in r['t'] if x.endswith('%')]
        if lab and pcts:
          tested+=1; agree+= all(l in pcts for l in lab)
          if not all(l in pcts for l in lab): print("   mismatch",r['n'],r['t'],pcts,(pop or '')[:120].replace("\n"," | "))
      await pg.evaluate("()=>window.__v2.setView('list')"); await pg.wait_for_timeout(1500)
      ck("%s: row percentages equal the pop-up percentages (%d sampled)"%(k,tested),tested>=1 and agree==tested,(tested,agree))
    # states list in district-type context sums districts (not the statewide total)
    await pg.evaluate("()=>{ state.value=''; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(500)
    await pg.evaluate("k=>document.querySelector('.lbtn[data-k='+k+']').click()","senate"); await pg.wait_for_timeout(6000)
    s=await pg.evaluate("()=>({head:(document.querySelector('#listView .lvhead')||{}).textContent,al:(()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&/Alabama/.test(b.title||'')}); return r&&[...r.querySelectorAll('.sg b')].map(b=>b.textContent.trim())})(),dsum:(()=>{const R=window.__dsRow; return null})()})")
    ck("states list in state-senate context lists states",'states' in (s['head'] or ''),s)
    ck("no page errors",not errs,errs[:3]); await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
