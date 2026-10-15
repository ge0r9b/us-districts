# t235/t236/t237: no text under the floating button column (any list level, any mode); delta shows only the net value next to the winner thumbnail
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
CHK="""()=>{ const lv=document.getElementById('listView'); const vis=e=>{const r=e.getBoundingClientRect(); return r.width>0&&r.height>0&&getComputedStyle(e).display!=='none'};
 let L=1e9; document.querySelectorAll('.rail .rbtn,#bGeo,#bGlobe,#bNum,#bLyr,#bTime,#bSearch,#bChart,.xrow .lbtn').forEach(b=>{ if(vis(b)){ const r=b.getBoundingClientRect(); if(r.left>innerWidth*0.5&&r.left<L) L=r.left; } });
 const bad=[]; let nodes=0; const tw=document.createTreeWalker(lv,NodeFilter.SHOW_TEXT);
 while(tw.nextNode()){ const n=tw.currentNode; if(!n.textContent.trim()) continue; const el=n.parentElement; const cs=getComputedStyle(el); if(cs.visibility==='hidden'||cs.display==='none') continue; let hid=false; for(let e=el;e&&e!==lv;e=e.parentElement){ const c=getComputedStyle(e); if(c.visibility==='hidden'||c.display==='none') hid=true; } if(hid) continue;
   const rg=document.createRange(); rg.selectNodeContents(n); for(const r of rg.getClientRects()){ if(r.width<=0) continue; nodes++; if(r.right>L+0.5&&r.left<innerWidth) bad.push([n.textContent.trim().slice(0,12),Math.round(r.left),Math.round(r.right)]); } }
 const rows=[...lv.querySelectorAll('.lvrow.la')]; const net=rows.map(r=>{const n=r.querySelector('.net'), t=r.querySelector('.sth'); if(!n||!t) return null; const a=n.getBoundingClientRect(), b=t.getBoundingClientRect(); return [Math.round(a.left-b.right)]}).filter(Boolean);
 return {L:Math.round(L),bad:bad.slice(0,6),nbad:bad.length,nodes,rows:rows.length,segTxt:lv.querySelectorAll('.sbw .sg b').length,nets:lv.querySelectorAll('.net').length,scg:[...lv.querySelectorAll('.scg')].filter(vis).length,netGap:net.slice(0,5),withData:rows.filter(r=>r.querySelector('.sbw:not(.nd)')).length}}"""
async def run(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  for mode in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1500)
    r=await pg.evaluate(CHK); ck(tag+" states list %s: no text under the button column (L=%s, %d text boxes)"%(mode,r['L'],r['nodes']),r['nbad']==0 and r['nodes']>50,r)
    ck(tag+" states list %s: segment labels still present"%mode,r['segTxt']>20,r)
  # delta
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=1; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(500)
  await pg.wait_for_timeout(1500)
  for mode in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1500)
    r=await pg.evaluate(CHK); ck(tag+" delta %s: no text under the button column"%mode,r['nbad']==0 and r['nodes']>20,r)
    ck(tag+" delta %s: net value column present on every row with data, no right-edge margin"%mode,r['scg']==0 and r['nets']>=r['withData']>20,r)
  await pg.screenshot(path="/tmp/lc-%s-delta.png"%tag)
  # a county level (Alabama counties) in each mode
  await pg.evaluate("()=>{ state.value='Alabama'; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(2500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5500)
  for mode in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1500)
    r=await pg.evaluate(CHK); ck(tag+" Alabama counties delta %s: no text under button column"%mode,r['nbad']==0 and r['nodes']>20,r)
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"phone",{"width":390,"height":780},True); await run(b,"desktop",{"width":1280,"height":800},False)
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
