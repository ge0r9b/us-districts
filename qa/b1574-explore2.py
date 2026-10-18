import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from restore import slider_to, chart
PAGE="()=>({ym:window.__ymode(),raw:window.__ymRaw&&window.__ymRaw(),y16:window.__y16,hi:window.__y16hi,ysl:window.__ysl.get(),chart:window.chartMode,lv:window.__laInfo().on?window.__laInfo().lv:'-',body:document.body.className,thumbs:[...document.querySelectorAll('.cand')].filter(b=>b.offsetParent).map(b=>b.getAttribute('aria-label')+' :: '+b.innerText.replace(/\\n/g,' ')),opts:[...document.querySelectorAll('#chartBox .copts button')].map(b=>b.dataset.ch+(b.offsetParent?'':'(hidden)')+(b.disabled?'(dis)':'')),ynote:document.getElementById('ynote').textContent,hdr:(document.getElementById('crumbs')||{}).innerText,rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,5).map(r=>r.innerText.replace(/\\n/g,' | ').slice(0,100))})"
async def drag(pg,i0,i1):
  # synthetic touch pointer drag on the year track from tick i0 to tick i1
  return await pg.evaluate("""([i0,i1])=>new Promise(res=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;const x=i=>r.left+52+i/(N-1)*(r.width-104);const y=r.top+r.height/2;
   const ev=(t,cx)=>w.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:7,pointerType:'touch',isPrimary:true,clientX:cx,clientY:y}));
   ev('pointerdown',x(i0));let k=0;const steps=8;const f=()=>{k++;ev('pointermove',x(i0)+(x(i1)-x(i0))*k/steps);if(k<steps)requestAnimationFrame(f);else{ev('pointerup',x(i1));res(window.__ysl.get())}};requestAnimationFrame(f)})""",[i0,i1])
async def main():
  eng=sys.argv[1] if len(sys.argv)>1 else 'chromium'
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,390,844,True,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    print('BUILD',await pg.evaluate("window.BUILD"))
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    print('start',json.dumps(await pg.evaluate(PAGE)))
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
    await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000)
    print('20>24',json.dumps(await pg.evaluate(PAGE))); await pg.screenshot(path='../shots/b1574-explore-20-24.png')
    print('drag',await drag(pg,1,0)); await pg.wait_for_timeout(6000)
    print('16>24',json.dumps(await pg.evaluate(PAGE)))
    await pg.evaluate("()=>document.querySelector('#chartBox .cmain').click()"); await pg.wait_for_timeout(700)
    print('after menu open',await pg.evaluate("()=>window.__ysl.get()"))
    await pg.evaluate("()=>document.querySelector('#chartBox .copts button[data-ch=line]').click()"); await pg.wait_for_timeout(3000)
    print('line',json.dumps(await pg.evaluate(PAGE))); await pg.screenshot(path='../shots/b1574-explore-line.png')
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(4000)
    print('set16(2) with line',json.dumps(await pg.evaluate(PAGE))); await pg.screenshot(path='../shots/b1574-explore-line16.png')
    await pg.evaluate("()=>document.querySelector('#chartBox .cmain').click()"); await pg.wait_for_timeout(700)
    print('menu2',json.dumps(await pg.evaluate(PAGE)))
    await pg.evaluate("()=>document.querySelector('#chartBox .copts button[data-ch=bar]')?document.querySelector('#chartBox .copts button[data-ch=bar]').click():document.body.click()"); await pg.wait_for_timeout(3000)
    print('bar',json.dumps(await pg.evaluate(PAGE)))
    cb=await pg.evaluate("()=>document.getElementById('chartBox').outerHTML.slice(0,1500)"); print(cb)
    print('err',log)
    await c.close(); await b.close()
asyncio.run(main())
