# t250u: line chart auto-falls back to bar on a single year (restored on two points); chart button is dark only when a chart is displayed (not in full-screen map)
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
ST="()=>{ const m=document.querySelector('[aria-label=Chart]'); return {mode:window.chartMode,ico:m.dataset.ch,on:m.classList.contains('on'),yv:+document.getElementById('yslider').value,view:window.__v2&&0,lm:document.body.classList.contains('listmode'),r:(r=>[r.left,r.top,r.width,r.height])(m.getBoundingClientRect()),vis:getComputedStyle(m).visibility+'/'+getComputedStyle(m).display} }"
async def pick(pg,k):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(400)
  await pg.evaluate("m=>{ const b=[...document.querySelectorAll('button')].find(b=>b.dataset&&b.dataset.ch===m&&b.closest('.copts')); b&&b.click(); }",k); await pg.wait_for_timeout(1200)
async def sv(pg,v):
  want=(v=='list'); cur=await pg.evaluate("()=>document.body.classList.contains('listmode')")
  if cur!=want: await pg.evaluate("()=>document.getElementById('bGlobe').click()")
  await pg.wait_for_timeout(300)
async def opts(pg):
  await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(400)
  o=await pg.evaluate("()=>[...document.querySelectorAll('.copts button')].map(b=>b.dataset.ch)")
  await pg.evaluate("()=>document.getElementById('chartDim').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,cancelable:true}))"); await pg.wait_for_timeout(400); return o
async def slide(pg,v):
  await pg.evaluate("v=>{ const s=document.getElementById('yslider'); s.value=v; s.dispatchEvent(new Event('input',{bubbles:true})); }",v); await pg.wait_for_timeout(900)
async def run(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>{ state.value='Alabama'; state.onchange&&state.onchange(); }"); await pg.wait_for_timeout(2500)
  await pg.evaluate("()=>{ county.value='Autauga County'; county.onchange&&county.onchange(); }"); await pg.wait_for_timeout(3000)
  await sv(pg,"list"); await pg.wait_for_timeout(1200)
  o=await opts(pg); ck(tag+" fresh single point: menu offers pie (not line)",o==["pie"],o)
  await slide(pg,1); o=await opts(pg); ck(tag+" range: menu offers line (not pie)",o==["line"],o)
  await pick(pg,"line"); s=await pg.evaluate(ST)
  ck(tag+" line selected -> two-point range, button dark with line icon",s['mode']=="line" and s['yv']==1 and s['on'] and s['ico']=="line",s)
  await slide(pg,2); s=await pg.evaluate(ST)
  ck(tag+" slider to single year 2024 -> line off, falls back to bar",s['mode']=="bar" and s['ico']=="bar" and s['yv']==2,s)
  ck(tag+" ...button not showing the line icon; dark because a (bar) chart is displayed",s['ico']!="line" and s['on'],s)
  await pg.wait_for_timeout(1500); s2=await pg.evaluate(ST); ck(tag+" ...stays bar (not forced back to a range)",s2['mode']=="bar" and s2['yv']==2,s2); ck(tag+" ...button did not move",s['r']==s2['r'],(s['r'],s2['r']))
  r=await pg.evaluate("()=>({line:!!document.querySelector('.dlch,.clinechart'),bar:!!document.querySelector('.cpanel,.cblk,.cbar,.cwideWrap')})"); ck(tag+" ...no line graph displayed",not r['line'],r)
  await slide(pg,1); s=await pg.evaluate(ST); ck(tag+" back to two points -> line restored",s['mode']=="line" and s['ico']=="line" and s['on'],s)
  await slide(pg,0); s=await pg.evaluate(ST); ck(tag+" single year 2020 -> bar too",s['mode']=="bar",s)
  await slide(pg,1); s=await pg.evaluate(ST); ck(tag+" 2020 -> two points restores line",s['mode']=="line",s)
  # RULE t251-t254: single point = bar+pie; range = bar+line; the button only cycles valid types; auto-switch + restore
  await slide(pg,2); s=await pg.evaluate(ST); ck(tag+" single point, line was on -> bar",s['mode']=="bar",s)
  o=await opts(pg); ck(tag+" single point menu offers pie only (no line)",o==["pie"],o)
  await pick(pg,"pie"); s=await pg.evaluate(ST); ck(tag+" single point: pie selectable",s['mode']=="pie" and s['on'] and s['ico']=="pie",s)
  r=await pg.evaluate("()=>({pie:!!document.querySelector('.cpie1,.cpieL,.pwr')})"); ck(tag+" single point: pie chart displayed",r['pie'],r)
  await slide(pg,1); s=await pg.evaluate(ST); ck(tag+" pie + range -> bar (no pie in a range)",s['mode']=="bar" and s['ico']=="bar",s)
  r=await pg.evaluate("()=>({pie:!!document.querySelector('.cpie1,.cpieL')})"); ck(tag+" range: no pie / concentric ring displayed",not r['pie'],r)
  o=await opts(pg); ck(tag+" range menu offers line only (no pie)",o==["line"],o)
  await slide(pg,2); s=await pg.evaluate(ST); ck(tag+" back to a single point -> pie restored",s['mode']=="pie",s)
  await slide(pg,1); await slide(pg,2); await pick(pg,"bar"); s=await pg.evaluate(ST)
  await slide(pg,1); s=await pg.evaluate(ST); ck(tag+" after choosing bar manually, a range stays bar (no stale restore)",s['mode']=="bar",s)
  await slide(pg,2); s=await pg.evaluate(ST); ck(tag+" ...and a single point stays bar",s['mode']=="bar",s)
  await slide(pg,1); await pick(pg,"line"); s=await pg.evaluate(ST); ck(tag+" line selectable in range",s['mode']=="line" and s['yv']==1,s)
  # map view: button inactive, list: active
  await pick(pg,"line"); s=await pg.evaluate(ST); ck(tag+" line on again",s['mode']=="line" and s['on'],s)
  await sv(pg,"map"); await pg.wait_for_timeout(900); m=await pg.evaluate(ST)
  ck(tag+" full-screen map: chart button in the inactive style (no dark 'on')",not m['on'] and m['vis'].startswith('visible'),m)
  await sv(pg,"list"); await pg.wait_for_timeout(900); l=await pg.evaluate(ST)
  ck(tag+" back in list view: chart button dark again, same type",l['on'] and l['mode']=="line",l)
  await sv(pg,"map"); await pg.wait_for_timeout(500); await slide(pg,2); m=await pg.evaluate(ST); ck(tag+" map + single year: bar fallback, button inactive",m['mode']=="bar" and not m['on'],m)
  await slide(pg,1); m=await pg.evaluate(ST); ck(tag+" map + two points: line restored, button still inactive",m['mode']=="line" and not m['on'],m)
  await pg.screenshot(path="/tmp/cls-%s-map.png"%tag)
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"phone",{"width":390,"height":780},True); await run(b,"desktop",{"width":1280,"height":800},False)
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
