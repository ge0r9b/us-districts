import asyncio,json
from playwright.async_api import async_playwright
from common import *
from restore import slider_to, chart
async def main():
  async with async_playwright() as p:
    import sys; eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    await slider_to(pg,0); await pg.wait_for_timeout(6000)
    g=await pg.evaluate("()=>Object.keys(window).filter(k=>/2016|16$/i.test(k)).map(k=>[k,typeof window[k],window[k]&&typeof window[k]=='object'?Object.keys(window[k]).slice(0,5):''])")
    print('globals',json.dumps(g)[:1500])
    # range via knob drag: go to range first
    await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(4000)
    kn=await pg.evaluate("()=>[...document.querySelectorAll('.kn')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})")
    trk=await pg.evaluate("()=>{const t=document.querySelector('.trk').getBoundingClientRect();return [t.left,t.right]}")
    print('knobs',kn,'trk',trk)
    left=min(kn,key=lambda k:k[0])
    cdp=await c.new_cdp_session(pg)
    async def touch(t,x,y): await cdp.send('Input.dispatchTouchEvent',{'type':t,'touchPoints':[] if t=='touchEnd' else [{'x':x,'y':y}]})
    await touch('touchStart',*left)
    for i in range(1,11): await touch('touchMove',left[0]-(left[0]-trk[0])*i/10,left[1]); await pg.wait_for_timeout(30)
    await touch('touchEnd',0,0)
    T=[]
    for t in (300,1500,4000,10000):
      await pg.wait_for_timeout(t-(T[-1][0] if T else 0))
      T.append([t,await pg.evaluate("()=>({loading:/Loading 2016/.test(document.body.innerText),thumbs:[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')),rows:[...document.querySelectorAll('#listView .lvrow.la')].slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | ')),knobs:[...document.querySelectorAll('.kn')].filter(e=>e.offsetParent).map(e=>Math.round(e.getBoundingClientRect().left)),chart:window.chartMode})")])
      await safeshot(pg,f"../shots/b1574-{eng[:2]}-{W}-y16-range16-{t}ms.png")
    for x in T: print(json.dumps(x)[:700])
    await chart(pg,'line'); await pg.wait_for_timeout(1500); print('line',await pg.evaluate("()=>window.chartMode")); await safeshot(pg,f"../shots/b1574-{eng[:2]}-{W}-y16-range16-line.png")
    await chart(pg,'pie'); print('pie in range ->',await pg.evaluate("()=>window.chartMode"))
    # reload restore of range from 16
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
    print('after reload',await pg.evaluate("()=>({loading:/Loading 2016/.test(document.body.innerText),thumbs:[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')),knobs:[...document.querySelectorAll('.kn')].filter(e=>e.offsetParent).map(e=>Math.round(e.getBoundingClientRect().left)),chart:window.chartMode,rows:[...document.querySelectorAll('#listView .lvrow.la')].slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))})"))
    await safeshot(pg,f"../shots/b1574-{eng[:2]}-{W}-y16-range16-reload.png")
    print('err',log['pageerr'],log['console'][:5]); await c.close(); await b.close()
asyncio.run(main())
