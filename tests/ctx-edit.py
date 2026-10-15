# t206: from a district list, tap the top 'Alabama' row -> institution field with full state list; type texas + Enter -> Texas; menu pick; Escape returns
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
ST="()=>{const r=e=>{const b=e&&e.getBoundingClientRect(); return b?[Math.round(b.left),Math.round(b.top)]:null}; const l=document.getElementById('ctxList'); const li=l&&l.querySelector('li:not([style*=none])'); return {sheet:getComputedStyle(document.getElementById('sheet')).display,ctx:document.body.classList.contains('ctxedit'),n:l?[...l.children].filter(x=>x.style.display!=='none').length:0,st:state.value,lt:((document.querySelector('#barGeo .fsqlbl span')||{}).textContent||''),top:(document.querySelector('#crumbs .tbScope')||{}).textContent,topv:!!document.querySelector('#crumbs .tbScope')&&document.querySelector('#crumbs .tbScope').offsetParent!==null,bs:Math.round(document.getElementById('barSearch').getBoundingClientRect().top),bg:Math.round(document.getElementById('barGeo').getBoundingClientRect().top),ix:li?Math.round(li.querySelector('.oic').getBoundingClientRect().left+li.querySelector('.oic').getBoundingClientRect().width/2):null,nx:li?Math.round(li.querySelector('.nm').getBoundingClientRect().left):null}}"
async def go(pg,tag):
  await pg.evaluate('()=>{try{localStorage.clear()}catch(e){}}') if pg.url!='about:blank' else None
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500)
  await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
  await pg.click("#bGeo"); await pg.wait_for_timeout(1200)
  await pg.evaluate("()=>document.querySelector('.lbtn[data-k=senate]').click()"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
async def run(b,tag,vp):
  errs=[]
  async def fresh():
    c=await b.new_context(viewport=vp); q=await c.new_page(); q.on('pageerror',lambda e:errs.append(str(e)[:150])); return q
  pg=await fresh()
  await go(pg,tag); s=await pg.evaluate(ST); ck(tag+" district menu open, top row Alabama visible",s['topv'] and s['top'].strip()=='Alabama' and 'senate' in s['lt'].lower(),s)
  await pg.evaluate("()=>document.querySelector('#crumbs .tbScope').click()"); await pg.wait_for_timeout(900); s=await pg.evaluate(ST)
  ck(tag+" tap Alabama -> full state list in the field",s['ctx'] and s['n']>=50 and s['topv'] and s['bs']==8 and s['bg']==64,s)
  ck(tag+" state rows: flag icon x=27, text x=52",s['ix'] is not None and abs(s['ix']-27)<=2 and abs(s['nx']-52)<=2,s)
  await pg.screenshot(path="/workspace/shots/ce-%s-list.png"%tag)
  await pg.keyboard.type("texas"); await pg.wait_for_timeout(500); s=await pg.evaluate(ST); ck(tag+" typing filters",s['n']<=3 and s['ctx'],s)
  await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4000); s=await pg.evaluate(ST); ck(tag+" Enter selects Texas, district type kept",s['st']=='Texas' and not s['ctx'] and 'senate' in s['lt'].lower(),s)
  pg=await fresh(); await go(pg,tag); await pg.evaluate("()=>document.querySelector('#crumbs .tbScope').click()"); await pg.wait_for_timeout(800)
  await pg.keyboard.press("Escape"); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(tag+" Escape returns to Alabama district menu",s['st']=='Alabama' and not s['ctx'] and s['sheet']!='none' and s['topv'],s)
  pg=await fresh(); await go(pg,tag); await pg.evaluate("()=>document.querySelector('#crumbs .tbScope').click()"); await pg.wait_for_timeout(800)
  await pg.evaluate("()=>{[...document.querySelectorAll('#ctxList li')].find(l=>l.textContent.trim()==='Georgia').click()}"); await pg.wait_for_timeout(4000); s=await pg.evaluate(ST); ck(tag+" menu pick Georgia",s['st']=='Georgia' and not s['ctx'],s)
  ck(tag+" no page errors",not errs,errs)
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch(); await run(b,'dk',{"width":1280,"height":800}); await run(b,'ph',{"width":390,"height":780}); await b.close()
  print('FAILS',fails)
asyncio.run(m())
