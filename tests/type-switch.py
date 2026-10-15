# t223/t224: switching district type (or state via menu) from a list-all view re-renders immediately, keeps list view/format/sort, never shows the empty body or the results block
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
ST="""()=>{const vis=e=>e&&e.offsetParent&&e.getBoundingClientRect().width>0; const lv=document.getElementById('listView'); const rows=lv?[...lv.querySelectorAll('.lvrow')].filter(vis).length:0; const c=document.getElementById('cands');
 return {la:document.body.classList.contains('listall'),fs:document.body.classList.contains('foldfs'),view:window.__v2.view,rows,cands:!!(c&&vis(c)&&c.children.length&&getComputedStyle(c).display!=='none'),top:(document.getElementById('vtitle')||{}).textContent,geo:document.getElementById('gq').placeholder,crumb:[...document.querySelectorAll('#crumbs .crumb')].filter(vis).map(x=>x.textContent.trim()).join('>'),lt:(document.querySelector('#lyrRow .lbtn.on')||{dataset:{}}).dataset.k,st:state.value,bLyr:!!vis(document.getElementById('bLyr'))||!!vis(document.querySelector('#lyrRow .lbtn')),bGeo:!!vis(document.getElementById('bGeo')),sort:!!document.querySelector('#laSort,.lasort'),first:(lv.querySelector('.lvrow b.rn')||{}).textContent||''}}"""
FR="""()=>{window.__fr=[]; const f=()=>{ const lv=document.getElementById('listView'); const c=document.getElementById('cands'); const vis=e=>e&&e.offsetParent&&e.getBoundingClientRect().width>0; window.__fr.push([lv?[...lv.querySelectorAll('.lvrow')].filter(vis).length:0, !!(c&&vis(c)&&c.children.length)]); window.__frid=requestAnimationFrame(f); }; f(); }"""
async def run(b,tag,vp):
  errs=[]
  c=await b.new_context(viewport=vp); pg=await c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(4000)
  await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  s0=await pg.evaluate(ST); ck(tag+" start: AL school districts list-all",s0['la'] and s0['rows']>100 and s0['lt']=='schools',s0)
  for k,exp in (("senate",35),("statehouse",105),("ushouse",7),("schools",141)):
    await pg.evaluate(FR)
    await pg.evaluate("k=>{const x=document.querySelector('.lbtn[data-k='+k+']'); x.click()}",k); await pg.wait_for_timeout(3500)
    fr=await pg.evaluate("()=>{cancelAnimationFrame(window.__frid); return window.__fr}")
    s=await pg.evaluate(ST)
    ck(tag+" %s: list-all re-rendered (%d rows), list view, top/geo rows kept"%(k,exp),s['la'] and s['view']=='list' and s['rows']==exp and s['lt']==k and s['top']=='President' and s['geo']=='Alabama' and s['crumb']=='Alabama' and s['bGeo'],s)
    ck(tag+" %s: no frame with empty body or results block"%k,all(r[0]>0 and not r[1] for r in fr),[r for r in fr if r[0]==0 or r[1]][:5])
  # menu path: switch state from the menu while list-all
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1800)
  await pg.evaluate("()=>document.querySelector('#crumbs .tbScope').click()"); await pg.wait_for_timeout(900)
  await pg.keyboard.type("ohio"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(6000)
  s=await pg.evaluate(ST); ck(tag+" menu: Alabama -> Ohio, menu stays on Ohio school districts",s['fs'] and s['st']=='Ohio' and s['crumb']=='Ohio',s)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(4000)
  s=await pg.evaluate(ST); ck(tag+" menu closed -> Ohio school-district list-all, rows rendered, list view kept, top/geo rows",s['la'] and not s['fs'] and s['st']=='Ohio' and s['rows']>100 and s['view']=='list' and s['top']=='President' and s['crumb']=='Ohio' and s['lt']=='schools',s)
  # menu path: pick a district-type via the menu header, back to statewide
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"desktop",{"width":1280,"height":800}); await run(b,"phone",{"width":390,"height":780})
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
