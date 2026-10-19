# t225-t230: back button + history stack. Button exists only with a non-empty stack, only in filter lists / list views. Back pops one change.
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
S="""()=>{const vis=e=>e&&e.getBoundingClientRect().width>0&&getComputedStyle(e).display!=='none'; const b=document.getElementById('bBack'); const r=b.getBoundingClientRect(); const so=document.getElementById('laSort'); const sr=so.getBoundingClientRect(); const C=e=>{if(!e)return null;const q=e.getBoundingClientRect();return q.height>0?q.top+q.height/2:null}; const tb=document.getElementById('bTime'); return {fs:document.body.classList.contains('foldfs'),btn:!!vis(b),box:[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)],cy:r.top+r.height/2,cx:r.left+r.width/2,texp:tb.classList.contains('on'),clockCy:C(tb),chartCy:C(document.querySelector('button.rbtn.cmain')),glyph:document.querySelector('#bBack svg').getBoundingClientRect().width,rg:document.querySelector('#laSort svg').getBoundingClientRect().height,sortCy:vis(so)?C(so):null,bg:getComputedStyle(b).backgroundColor,sortbox:vis(so)?[Math.round(sr.left),Math.round(sr.top),Math.round(sr.width),Math.round(sr.height)]:null,depth:window.__backDepth(),st:state.value,co:county.value,w:window.__W&&window.__W(),lt:(document.querySelector('#lyrRow .lbtn.on')||{dataset:{}}).dataset.k||'',la:document.body.classList.contains('listall'),view:window.__v2.view,sort:window.__laInfo().sort,lv:window.__laInfo().lv,rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).length,top:window.__stateSnapshot().top,url:location.pathname,lvTop:document.getElementById('listView').getBoundingClientRect().top,row1:(()=>{const lt=document.getElementById('listView').getBoundingClientRect().top;const r=[...document.querySelectorAll('#listView .lvrow.la')].map(x=>x.getBoundingClientRect()).find(q=>q.height>0&&q.top>=lt-1);return r?r.top:null})()}}"""
async def fresh(b,vp,geo=None):
  c=await b.new_context(viewport=vp); await c.add_init_script('window.__noDistTier=1'); pg=await c.new_page(); pg.errs=[]; pg.on('pageerror',lambda e:pg.errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3800)
  if geo:
    await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(geo); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3800)
  return pg
async def tog(pg): await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1600)
async def run(b,tag,vp):
  # A: fresh load -> none; search selection pushes; button only in filter lists / list views
  pg=await fresh(b,vp); s=await pg.evaluate(S); ck(tag+" fresh load: no back button, empty stack",not s['btn'] and s['depth']==0,s)
  await tog(pg); s=await pg.evaluate(S); ck(tag+" fresh load, filter open: still no button",s['fs'] and not s['btn'] and s['depth']==0,s); await tog(pg)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3800)
  s=await pg.evaluate(S); ck(tag+" search selection pushed (depth 1); on the map/results the button is hidden",s['depth']==1 and not s['btn'] and s['st']=='Alabama',s)
  await tog(pg); s=await pg.evaluate(S); ck(tag+" filter list: no stray chevron over the institution filter (build 1555), stack kept",s['fs'] and not s['btn'] and s['depth']==1,s)
  await pg.screenshot(path="/tmp/fb-%s-filter.png"%tag)
  await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(2500); s=await pg.evaluate(S); ck(tag+" back: Alabama -> United States restored, stack empty, button gone",s['st']=='' and s['depth']==0 and not s['btn'],s)
  # B: menu pick pushes (county row inside the state's menu)
  await pg.context.close(); pg=await fresh(b,vp,"alabama"); await tog(pg)
  s=await pg.evaluate(S); d0=s['depth']
  await pg.evaluate("()=>{const l=[...document.querySelectorAll('#sheet .foldlist li')].find(x=>/Mobile County/.test(x.textContent)); l&&l.click()}"); await pg.wait_for_timeout(3500)
  s=await pg.evaluate(S); ck(tag+" menu pick (Mobile County) pushed",s['co']=='Mobile County' and s['depth']==d0+1,s)
  if not s['fs']: await tog(pg)
  s=await pg.evaluate(S); ck(tag+" filter list: no chevron (build 1555)",s['fs'] and not s['btn'],s)
  await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(3000); s=await pg.evaluate(S); ck(tag+" back restores Alabama (county cleared), one entry left",s['co']=='' and s['st']=='Alabama' and s['depth']==d0,s)
  await pg.context.close()
  # C: topic switch pushes
  pg=await fresh(b,vp,"alabama"); await tog(pg); await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(2000); await tog(pg)
  await pg.evaluate("()=>window.__setTopic(null)"); await pg.wait_for_timeout(1500); s=await pg.evaluate(S); ck(tag+" topic switch pushed",s['depth']==1 and s['top']=='-',s)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500); s=await pg.evaluate(S); ck(tag+" topic: no chevron over the filter list (build 1555)",s['fs'] and not s['btn'],s)
  await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(2000); s=await pg.evaluate(S); ck(tag+" topic back restores President, button gone",s['top']!='-' and s['depth']==0 and not s['btn'],s)
  await pg.context.close()
  # D: list view: US states list-all -> tap state -> its counties -> back x1; settings persist; alignment with sort control; time filter expanded
  pg=await fresh(b,vp); await tog(pg); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
  s=await pg.evaluate(S); ck(tag+" states list-all, fresh: no button",s['la'] and not s['btn'] and s['depth']==0,s)
  await pg.evaluate("()=>{ if(window.__laInfo().sort!=='asc') document.getElementById('laSort').click(); }"); await pg.wait_for_timeout(800)
  await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(800)
  await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const b=r.querySelector('b.rn'); return b&&/Alabama/.test(b.title||b.textContent)}).click()"); await pg.wait_for_timeout(7000)
  s=await pg.evaluate(S); ck(tag+" tap Alabama -> its counties list-all, depth 1, chevron visible: x half-way from the icon column (27) to the edge, glyph >=10px from it (18.5), (chevron-height rule retired: since 1594/1595 the chevron and sort chip sit on the first row's resting top), no background, glyph = sort-glyph size, sort glyph on the same line, 44 px target",s['la'] and s['st']=='Alabama' and s['depth']==1 and s['btn'] and abs(s['cx']-18.5)<=1.5 and not s['texp'] and s['box'][2]>=44 and s['box'][3]>=44 and s['bg'] in ('rgba(0, 0, 0, 0)','transparent') and abs(s['glyph']-s['rg'])<=1.5 and s['sortCy'] is not None and abs(s['sortCy']-s['cy'])<=1.5,s)
  await pg.screenshot(path="/tmp/fb-%s-list.png"%tag)
  await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(900); s2=await pg.evaluate(S)
  ck(tag+" time filter expanded: chevron and sort glyph on one line (height rule retired, see 1595)",s2['btn'] and s2['sortCy'] is not None and abs(s2['sortCy']-s2['cy'])<=1.5 and s2['texp'] and abs(s2['cx']-18.5)<=1.5,(s,s2))
  await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(700)
  await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(6000); s=await pg.evaluate(S); ck(tag+" back -> states list-all again, depth 0, button gone, format kept, sort back to the default high-to-low (build 1551: a re-entered list starts high-to-low)",s['la'] and s['st']=='' and s['lv']=='states' and s['depth']==0 and not s['btn'] and s['sort']=='desc' and s['view']=='list',s)
  await pg.context.close()
  # E: district-type switch -> back; keyboard; browser back
  pg=await fresh(b,vp,"alabama"); await tog(pg); await pg.evaluate("()=>document.querySelector('.lbtn[data-k=schools]').click()"); await pg.wait_for_timeout(3500)
  await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
  s0=await pg.evaluate(S); d0=s0['depth']
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=senate]').click()"); await pg.wait_for_timeout(3500); s=await pg.evaluate(S)
  ck(tag+" district-type switch pushed; list shows senate; button visible",s['lt']=='senate' and s['depth']==d0+1 and s['btn'] and s['rows']==35,s)
  await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(5000); s=await pg.evaluate(S); ck(tag+" back -> school districts list-all restored",s['lt']=='schools' and s['rows']>100 and s['depth']==d0 and s['la'],s)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=statehouse]').click()"); await pg.wait_for_timeout(3500)
  await pg.keyboard.press("Backspace"); await pg.wait_for_timeout(5000); s=await pg.evaluate(S); ck(tag+" Backspace (outside text field) steps back",s['lt']=='schools' and s['depth']==d0,s)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3500)
  await pg.keyboard.press("Alt+ArrowLeft"); await pg.wait_for_timeout(5000); s=await pg.evaluate(S); ck(tag+" Alt+Left steps back",s['lt']=='schools' and s['depth']==d0,s)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=senate]').click()"); await pg.wait_for_timeout(3500); u0=(await pg.evaluate(S))['url']
  await pg.go_back(); await pg.wait_for_timeout(5000); s=await pg.evaluate(S); ck(tag+" browser back steps back, stays in the app",s['lt']=='schools' and s['depth']==d0 and s['url']==u0,s)
  ck(tag+" no page errors",not pg.errs,pg.errs[:3]); await pg.context.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"desktop",{"width":1280,"height":800}); await run(b,"phone",{"width":390,"height":780})
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
