# usage: python3 tests/institution-icon-editing.py URL -- build 1558: the institution field (and its rows) ALWAYS shows institution icons:
# the flag-filled state shape while idle, focused/editing, typing every prefix, backspacing and on a full match; never the plain black
# geo silhouette (that belongs only to the bottom geo field, which keeps it).
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:600]); fails+=0 if ok else 1
F="""()=>{const f=document.querySelector('#barGeo .fsq'); const v=e=>{const r=e.getBoundingClientRect(); if(!(r.width>0&&r.height>0)) return false; for(let x=e;x&&x!==f.parentElement;x=x.parentElement){const cs=getComputedStyle(x); if(cs.display==='none'||cs.visibility==='hidden'||+cs.opacity===0) return false;} return true};
  const ic=[...f.querySelectorAll('.fsqrec > *, .fqi > *')].filter(v).map(e=>({tag:e.tagName, src:(e.getAttribute('src')||'').split('?')[0], fill:e.tagName==='svg'?getComputedStyle(e.querySelector('path')||e).fill:''}));
  const rows=[...document.querySelectorAll('#sheet li .oic > *, #orgSearch li .oic > *')].filter(v).map(e=>({tag:e.tagName, src:(e.getAttribute('src')||'').split('?')[0], row:(e.closest('li').querySelector('.nm')||{}).textContent}));
  return {val:(f.querySelector('input')||{}).value, ic, rows}}"""
def flagOK(r,st):
  return len(r['ic'])>=1 and all(i['tag']=='IMG' and i['src']==f"img/stateflags/{st.replace(' ','_')}.png" for i in r['ic'])
async def run(b,tag,vp,st):
  c=await b.new_context(viewport=vp,is_mobile=vp['width']<600,has_touch=vp['width']<600); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(400); await pg.keyboard.type(st.lower()); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3800)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  r=await pg.evaluate(F); ck(f"{tag} {st}: idle field icon is the flag-filled shape",flagOK(r,st),r['ic'])
  await pg.click("#barGeo .fsq"); await pg.wait_for_timeout(700); r=await pg.evaluate(F); ck(f"{tag} {st}: focused/editing (empty) field icon is the flag-filled shape",flagOK(r,st),r)
  bad=[]
  for i in range(1,len(st)+1):
    await pg.keyboard.type(st.lower()[i-1]); await pg.wait_for_timeout(180); r=await pg.evaluate(F)
    if not flagOK(r,st): bad.append((r['val'],r['ic']))
  ck(f"{tag} {st}: every typed prefix keeps the flag-filled shape",not bad,bad[:3])
  r=await pg.evaluate(F); sil=[x for x in r['rows'] if x['tag']=='svg' and x['row'] and x['row'].strip()==st]
  ck(f"{tag} {st}: institution rows show no silhouette for the state",not sil,r['rows'][:6])
  await pg.keyboard.press("Backspace"); await pg.keyboard.press("Backspace"); await pg.wait_for_timeout(400); r=await pg.evaluate(F); ck(f"{tag} {st}: backspacing keeps the flag-filled shape",flagOK(r,st),r)
  await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500); await pg.evaluate("()=>{ if(document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(900)
  # US level: rows for states use the flag-filled shape while typing
  await pg.evaluate("()=>{ const s=document.getElementById('state'); s.value=''; s.onchange&&s.onchange(); }"); await pg.wait_for_timeout(2500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500); await pg.click("#barGeo .fsq"); await pg.keyboard.type(st.lower()[:4]); await pg.wait_for_timeout(1000)
  r=await pg.evaluate(F); hit=[x for x in r['rows'] if (x['row'] or '').strip()==st]
  ck(f"{tag} US level typing '{st.lower()[:4]}': the {st} row has the flag-filled shape",hit and all(x['tag']=='IMG' and 'stateflags/' in x['src'] for x in hit),r['rows'][:6])
  await pg.keyboard.type(st.lower()[4:]); await pg.wait_for_timeout(900); r=await pg.evaluate(F)
  ck(f"{tag} US level, full name typed: field icon is the flag-filled shape",flagOK(r,st),r['ic'])
  await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500); await pg.evaluate("()=>{ if(document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(900)
  # geo field keeps the black silhouette
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type(st.lower()); await pg.wait_for_timeout(1500)
  g=await pg.evaluate("(st)=>{const l=[...document.querySelectorAll('#geofs li, #sheet li')].filter(x=>x.offsetParent&&(x.querySelector('.nm')||{}).textContent===st)[0]; return l?{svg:!!l.querySelector('.oic svg'),img:!!l.querySelector('.oic img')}:null}",st)
  ck(f"{tag} geo field: {st} row keeps the plain silhouette",g and g['svg'] and not g['img'],g)
  ck(f"{tag} no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp in (("ph",{"width":390,"height":844}),("dk",{"width":1280,"height":800})):
      for st in ("Pennsylvania","Alabama"): await run(b,tag,vp,st)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
