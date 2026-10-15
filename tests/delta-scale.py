# t238: delta list: abbreviation at x~44, net value column, stacked bar from |R chg|+|D chg|(+oth) on one common scale, thumbnail at bar's left end, nothing under the buttons
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else d); fails+=0 if ok else 1
Q="""()=>{ const lv=document.getElementById('listView'); let L=1e9; document.querySelectorAll('.rail .rbtn,#bGeo,#bGlobe,#bNum,#bLyr,#bTime,#bSearch,#bChart,.xrow .lbtn').forEach(b=>{const r=b.getBoundingClientRect(); if(r.width>0&&getComputedStyle(b).display!=='none'&&r.left>innerWidth*.5&&r.left<L) L=r.left});
 const rows=[...lv.querySelectorAll('.lvrow.la.cmp')].filter(r=>r.querySelector('.sbw.dl')); const out=rows.map(r=>{ const bar=r.querySelector('.sbw.dl').getBoundingClientRect(), rn=r.querySelector('b.rn .nmx').getBoundingClientRect(), net=r.querySelector('.net').getBoundingClientRect(), ic=r.querySelector('.oic').getBoundingClientRect(), th=r.querySelector('.sth'); const tr=th&&th.getBoundingClientRect(); const T=window.__dTot(r.__a); const segs=[...r.querySelectorAll('.sbw.dl .sg')].map(s=>s.getBoundingClientRect().width); return {w:bar.width,left:bar.left,right:bar.right,T,rn:rn.left,ic:ic.left+ic.width/2,netL:net.left,netR:net.right,thL:tr?tr.left:null,segSum:segs.reduce((a,b)=>a+b,0),grid:getComputedStyle(r.parentElement).getPropertyValue('--dlen')} });
 return {L,out} }"""
async def run(b,tag,vp,mobile):
  c=await b.new_context(viewport=vp,is_mobile=mobile,has_touch=mobile); pg=await c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:150]))
  await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  await pg.evaluate("()=>{ const s=document.getElementById('yslider'); s.value=1; s.dispatchEvent(new Event('input',{bubbles:true})); }"); await pg.wait_for_timeout(2500)
  for mode in ("pct","num"):
    await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(2000)
    r=await pg.evaluate(Q); o=r['out']; L=r['L']
    ck(tag+" %s: delta rows rendered"%mode,len(o)>=40,len(o))
    ck(tag+" %s: abbreviation starts at x~44, icon centre x=27"%mode,all(abs(x['rn']-44)<=1.5 and abs(x['ic']-27)<=1.5 for x in o),[(round(x['rn']),round(x['ic'])) for x in o[:3]])
    ck(tag+" %s: net value column sits after the abbreviation, before the bar"%mode,all(x['netL']>=x['rn'] and x['netR']<=x['left']+0.5 for x in o),o[:2])
    mx=max(o,key=lambda x:x['T']); ck(tag+" %s: largest total delta -> longest bar, ends left of the button column"%mode,mx['w']>=max(x['w'] for x in o)-1 and mx['right']<=L-5,(mx['w'],mx['right'],L))
    big=[x for x in o if x['w']>30 and x['T']>0]
    ck(tag+" %s: bar widths proportional to total delta (common scale)"%mode,all(abs(x['w']/mx['w']-x['T']/mx['T'])<0.02 for x in big),[(round(x['w']),round(x['T'],2)) for x in big[:4]])
    ck(tag+" %s: bars are NOT all stretched to one length"%mode,len({round(x['w']) for x in o})>=(10 if mode=='pct' else 3),sorted({round(x['w']) for x in o})[:6])
    ck(tag+" %s: stacked segments fill the bar; thumbnail at its left end"%mode,all(abs(x['segSum']-x['w'])<2 and (x['thL'] is None or abs(x['thL']-x['left'])<1.5) for x in o),o[:2])
  await pg.screenshot(path="/tmp/ds-%s-num.png"%tag)
  await pg.evaluate("()=>window.__setNum('pct')"); await pg.wait_for_timeout(1800); await pg.screenshot(path="/tmp/ds-%s-pct.png"%tag)
  ck(tag+" no page errors",not errs,errs[:3]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    await run(b,"phone",{"width":390,"height":780},True); await run(b,"desktop",{"width":1280,"height":800},False)
    await b.close()
  print("FAILS",fails); sys.exit(1 if fails else 0)
asyncio.run(main())
