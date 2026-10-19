# PREVIEW compact bars: panning or a map tap collapses the Topic and Institution bars to their icons (seal, flag) on the
# thumbnails' axis; a tap on an icon expands that bar; the Institution filter button is dark when expanded, light when
# collapsed; nothing moves (icons, thumbnails, buttons keep their rects). WebKit 390/375/320.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8846/v2/"; F=[]
def ck(c,m,x=None): print(("ok   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:300])); (None if c else F.append(m))
Q="""()=>{ const R=e=>{ const r=e.getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)] }; const vt=document.getElementById('vtitle'), seal=getComputedStyle(vt,'::before'); const sr=vt.getBoundingClientRect(); const cic=document.querySelector('#crumbs .cic');
 const th=[...document.querySelectorAll('#cands .cand img')].filter(e=>e.offsetParent).map(R); const B=document.body.classList;
 return {T:B.contains('cmpT'),G:B.contains('cmpG'), vtCol:getComputedStyle(vt).color, crumbOp:getComputedStyle(document.querySelector('#crumbs .crumb')).opacity, barBg:[getComputedStyle(document.getElementById('barSearch')).backgroundColor,getComputedStyle(document.getElementById('barGeo')).backgroundColor],
  geoDark:/rgba?\\(0, 0, 0/.test(getComputedStyle(document.getElementById('bGeo')).backgroundImage)||document.getElementById('bGeo').classList.contains('typed'), cic:R(cic), cicCx:cic.getBoundingClientRect().left+cic.getBoundingClientRect().width/2, sealVis:seal.backgroundImage!=='none', th, btns:[...document.querySelectorAll('.rbtn')].filter(e=>e.offsetParent).map(R)} }"""
async def tap(pg,sel):
  r=await pg.evaluate(f"()=>{{const e=document.querySelector('{sel}'); const r=e.getBoundingClientRect(); return [r.left+Math.min(r.width/2,18),r.top+r.height/2]}}"); await pg.touchscreen.tap(*r); await pg.wait_for_timeout(700)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch()
    for W,H in [(390,844),(375,667),(320,568)]:
      ctx=await b.new_context(viewport={'width':W,'height':H},has_touch=True,is_mobile=True); pg=await ctx.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000)
      q0=await pg.evaluate(Q)
      ck(not q0['T'] and not q0['G'] and q0['geoDark'],f"{W}: starts expanded, Institution button dark",q0)
      if W==390: await pg.screenshot(path="/workspace/prevshots/compact-expanded-390.png")
      # pan with a real touch drag on the map
      x,y=W/2,H*0.62
      cd=await ctx.new_cdp_session(pg) if False else None
      await pg.evaluate(f"()=>{{ const c=map.getContainer(); c.dispatchEvent(new PointerEvent('pointerdown',{{bubbles:true,clientX:{x},clientY:{y}}})); map.panBy([60,20],{{animate:false}}); return 1 }}"); await pg.wait_for_timeout(800)
      q1=await pg.evaluate(Q)
      ck(q1['T'] and q1['G'],f"{W}: panning collapses both bars",q1)
      ck(q1['vtCol'] in ('rgba(0, 0, 0, 0)','transparent') and float(q1['crumbOp'])==0 and q1['sealVis'] and all('0, 0, 0, 0' in c or c=='transparent' for c in q1['barBg']),f"{W}: collapsed = icons only (text and strips gone, seal and flag stay)",q1)
      ck(not q1['geoDark'],f"{W}: Institution button light when collapsed",q1)
      ck(q1['th']==q0['th'] and q1['cic']==q0['cic'] and q1['btns']==q0['btns'],f"{W}: nothing moves (thumbnails, flag, buttons)",[q0['btns'],q1['btns']])
      ck(abs(q1['cicCx']-(q1['th'][0][0]+q1['th'][0][2]/2))<=1.5 if q1['th'] else False,f"{W}: flag on the thumbnails' axis",[q1['cicCx'],q1['th'][:1]])
      if W==390: await pg.screenshot(path="/workspace/prevshots/compact-collapsed-390.png")
      await tap(pg,"#crumbs .cic"); q2=await pg.evaluate(Q)
      ck(not q2['G'] and q2['T'] and q2['geoDark'],f"{W}: tap the flag expands the Institution bar only; its button turns dark",q2)
      r=await pg.evaluate("()=>{const r=document.getElementById('vtitle').getBoundingClientRect();return [r.left+120,r.top+r.height/2]}"); await pg.touchscreen.tap(*r); await pg.wait_for_timeout(700); qx=await pg.evaluate(Q)
      ck(qx['T'],f"{W}: a tap on the hidden title text (not the seal) leaves the Topic bar collapsed",qx)
      await tap(pg,"#vtitle"); q3=await pg.evaluate(Q)
      ck(not q3['T'],f"{W}: tap the seal expands the Topic bar",q3)
      await pg.touchscreen.tap(W/2,H*0.6); await pg.wait_for_timeout(900); q4=await pg.evaluate(Q)
      ck(q4['T'] and q4['G'],f"{W}: a tap on the map collapses both",q4)
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1500); q5=await pg.evaluate(Q)
      ck(not q5['T'] and not q5['G'],f"{W}: list view always shows the bars",q5)
      ck(not er,f"{W}: no page errors",er); await ctx.close()
    await b.close()
  print("FAILS",len(F)); sys.exit(1 if F else 0)
asyncio.run(main())
