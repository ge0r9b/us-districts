# Build 1575 (user, live 1574): in the list (bar rows) the rows start half of the old blank band higher (old band 31px = 8px gap + 23px),
# so the first row slides halfway under the clear glass sort chip (the chip overlaps the row's top half); chip glass clearer; no jump.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
M="""()=>{const s=document.getElementById('laSort').getBoundingClientRect(), r=document.querySelector('#listView .lvgrid > .lvrow').getBoundingClientRect(), c=getComputedStyle(document.getElementById('laSort'),'::before');
 const lv=document.getElementById('listView').getBoundingClientRect(); return {chipTop:s.top,chipBot:s.bottom,chipMid:s.top+s.height/2,rowMid:r.top+r.height/2,rowTop:r.top,rowH:r.height,lvTop:lv.top,bg:c.backgroundImage,bf:c.backdropFilter||c.webkitBackdropFilter,bc:c.borderTopColor}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for vw,vh in ((390,844),(320,568),(1024,768),(1024,653)):
      pg=await b.new_page(viewport={'width':vw,'height':vh}); await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
      for lvl in ('All States','PA counties'):
        m=await pg.evaluate(M); old=m['lvTop']+31; want=old-31/2
        ck(abs(m['rowTop']-want)<=1.5,f"{vw}x{vh} {lvl}: first row top {m['rowTop']:.1f} = old top {old:.0f} - gap/2 ({want:.1f})",m)
        ck(m['chipBot']>m['rowTop']+4 and m['chipTop']<m['rowTop'] and m['chipMid']<=m['rowMid'],f"{vw}x{vh} {lvl}: the chip overlaps the first row's top half (chip {m['chipTop']:.0f}-{m['chipBot']:.0f}, row {m['rowTop']:.0f}-{m['rowTop']+m['rowH']:.0f})",m)
        ck('0.05' in m['bg'] and 'blur(3px)' in m['bf'] and m['bc']=='rgba(0, 0, 0, 0.85)',f"{vw}x{vh} {lvl}: clearer chip glass, crisp outline kept",m)
        ys=[]
        for i in range(8): ys.append(await pg.evaluate("()=>document.querySelector('#listView .lvgrid > .lvrow').getBoundingClientRect().top")); await pg.wait_for_timeout(120)
        ck(max(ys)-min(ys)<0.5,f"{vw}x{vh} {lvl}: first row steady",ys)
        if lvl=='All States':
          await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()"); await pg.wait_for_timeout(8000)
      if vw==390: await pg.screenshot(path='/workspace/rows-up-390.png')
      if vw==1024 and vh==768: await pg.screenshot(path='/workspace/rows-up-1024.png')
      await pg.close()
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
