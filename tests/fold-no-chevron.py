# usage: python3 tests/fold-no-chevron.py URL -- build 1555: no back chevron (#bBack) is visible while a full-screen filter is open
# (institution filter at US level and in a state, geographic filter), even with a non-empty history stack; it still shows in the list view.
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:400]); fails+=0 if ok else 1
V="""()=>{const b=document.getElementById('bBack'); const r=b?b.getBoundingClientRect():null; const all=[...document.querySelectorAll('#bBack, .bback, [aria-label=Back]')].filter(e=>{const q=e.getBoundingClientRect(); return q.width>0&&q.height>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'}).map(e=>e.id||e.className);
  const cl=document.body.classList; return {vis:all, canback:cl.contains('canback'), foldfs:cl.contains('foldfs'), geofs:cl.contains('geofs'), la:cl.contains('listall')}}"""
async def run(b,tag,vp):
  c=await b.new_context(viewport=vp); pg=await c.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>window.__setTopic(null)"); await pg.wait_for_timeout(1200); await pg.evaluate("()=>window.__setTopic('President')"); await pg.wait_for_timeout(1500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1600); s=await pg.evaluate(V)
  ck(tag+" US level, institution filter open (history non-empty): no back chevron",s['foldfs'] and s['canback'] and not s['vis'],s)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1000)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(500); await pg.keyboard.type("alabama"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3800)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1600); s=await pg.evaluate(V)
  ck(tag+" Alabama, institution filter open: no back chevron",s['foldfs'] and s['canback'] and not s['vis'],s)
  await pg.evaluate("()=>{const i=document.querySelector('#barGeo .fsq input'); i&&i.focus()}"); await pg.keyboard.type("ala"); await pg.wait_for_timeout(1000); s=await pg.evaluate(V)
  ck(tag+" Alabama, institution filter typing: no back chevron",not s['vis'],s)
  await pg.keyboard.press("Escape"); await pg.wait_for_timeout(600); await pg.evaluate("()=>{ if(document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1000)
  await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(1200); s=await pg.evaluate(V)
  ck(tag+" geographic filter open: no back chevron",s['geofs'] and not s['vis'],s)
  await pg.keyboard.press("Escape"); await pg.wait_for_timeout(800); await pg.evaluate("()=>document.getElementById('gq').blur()"); await pg.wait_for_timeout(600)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1600); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000); s=await pg.evaluate(V)
  ck(tag+" list view (Alabama counties): back chevron still available",s['la'] and not s['foldfs'] and '#bBack'.strip('#') in s['vis'],s)
  ck(tag+" no page errors",not errs,errs); await c.close()
async def m():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for tag,vp in (("ph",{"width":390,"height":780}),("dk",{"width":1280,"height":800})): await run(b,tag,vp)
    await b.close()
  print('FAILS',fails)
asyncio.run(m())
