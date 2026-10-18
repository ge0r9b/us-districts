# Build 1566: in results lists the sort chip sits one button width (48px) + a gap left of the right button column, on the back
# chevron's line; its 'High to low' bubble stays near it and clear of the buttons; the chip glass is half as opaque with fully dark
# arrows; every glass button / chip has a crisp 1px full-contrast outline and only a tight 0 1px 2px drop shadow.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
SHOT=sys.argv[2] if len(sys.argv)>2 else None
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
M="""()=>{const b=document.getElementById('laSort'),c=getComputedStyle(b,'::before'),br=b.getBoundingClientRect(),cl=br.left+parseFloat(c.left),ct=br.top+parseFloat(c.top);
 const col=[...document.querySelectorAll('.rbtn')].map(e=>e.getBoundingClientRect()).filter(r=>r.height>0&&r.left>innerWidth/2);
 const bk=document.querySelector('#bBack svg').getBoundingClientRect(), s=b.querySelector('svg'), ss=getComputedStyle(s);
 const btn=[...document.querySelectorAll('.rbtn,#bGeo,#bLyr,#barTime #bTime')].filter(e=>e.getBoundingClientRect().height>0).map(e=>{const k=getComputedStyle(e);return [e.id||e.className,k.borderTopWidth,k.borderTopColor,k.boxShadow]});
 return {chip:[cl,ct,cl+parseFloat(c.width),ct+parseFloat(c.height)],cy:ct+parseFloat(c.height)/2,colL:Math.min(...col.map(r=>r.left)),bkCy:bk.top+bk.height/2,bg:c.backgroundImage,cb:[c.borderTopWidth,c.borderTopColor,c.boxShadow],stroke:ss.stroke,op:ss.opacity,sw:s.getAttribute('stroke-width'),sz:[s.getBoundingClientRect().width,s.getBoundingClientRect().height],btn}}"""
async def run(b,W,H):
  c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=3 if W<500 else 2,is_mobile=W<500,has_touch=True); pg=await c.new_page()
  er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
  await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
  await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
  await pg.wait_for_selector('li.la-row',timeout=15000); await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
  await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(7000)
  for on in (False,True):
    if (await pg.evaluate("()=>!document.getElementById('barTime').hidden"))!=on: await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(1500)
    m=await pg.evaluate(M); t=f"{W}x{H} time {'open' if on else 'closed'}"
    ck(m['chip'][2]<=m['colL']-52,f"{t}: sort chip ends >=48px + gap left of the button column (chip right {m['chip'][2]:.0f}, column {m['colL']:.0f})",m)
    ck(m['chip'][2]>=m['colL']-80,f"{t}: ...but not far from it",m)
    ck(abs(m['cy']-m['bkCy'])<=2,f"{t}: sort chip on the back chevron's line",[m['cy'],m['bkCy']])
    if W==390: ck(200<=m['chip'][0]<=255,f"{t}: iPhone chip left in the marked x 205-250 band",m['chip'])
    ck('0.05' in m['bg'] and '0.03' in m['bg'],f"{t}: chip glass fill clearer (.05 / .03, build 1575)",m['bg'])
    ck(m['stroke']=='rgb(17, 17, 17)' and m['op']=='1' and m['sw']=='2' and abs(m['sz'][0]-21.75)<.1,f"{t}: arrows fully dark, same size and weight",m)
    ck(m['cb'][0]=='1px' and m['cb'][1]=='rgba(0, 0, 0, 0.85)' and '0px 1px 2px' in m['cb'][2] and '8px' not in m['cb'][2],f"{t}: chip has a crisp 1px outline + tight shadow",m['cb'])
    bad=[x for x in m['btn'] if x[1]!='1px' or '8px' in x[3] or '10px' in x[3]]
    ck(not bad and m['btn'],f"{t}: every glass button has a crisp 1px outline, no soft wide shadow",bad[:3])
    await pg.evaluate("()=>document.getElementById('laSort').click()"); await pg.wait_for_timeout(250)
    bb=await pg.evaluate("()=>{const e=document.getElementById('laSortBub'); if(!e||e.hidden) return null; const r=e.getBoundingClientRect(); return [r.left,r.top,r.right,r.bottom,e.textContent]}")
    ck(bb and bb[2]<=m['colL']-2 and abs((bb[0]+bb[2])/2-(m['chip'][0]+m['chip'][2])/2)<=45 and bb[1]>=m['chip'][3]-2,f"{t}: sort bubble below / near the chip, clear of the buttons",[bb,m['chip'],m['colL']])
    await pg.evaluate("()=>document.getElementById('laSort').click()"); await pg.wait_for_timeout(1700)
    if SHOT and W==390 and on:
      await pg.wait_for_timeout(1500); await pg.screenshot(path=SHOT)
  ck(not er,f"{W}x{H}: no page errors",er[:2]); await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in ((390,844),(375,667),(1024,576),(1024,768)): await run(b,W,H)
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
