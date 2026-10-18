# pass 14: QA-023 (Pittsburgh Enter), QA-025 (double-tap), QA-066/051 (All States '16 line), QA-018 (row bar tap), QA-061 (DC>DE field)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST,LI
async def boot(b,eng,W,H):
  c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); return c,pg,log
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}; pre=f"../shots/b1582p14-{eng[:2]}-{W}x{H}"
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    c,pg,log=await boot(b,eng,W,H); out['build']=await pg.evaluate('window.BUILD')
    await typegq(pg,'Pittsburgh'); out['pgh_sugg']=await pg.evaluate(LI); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
    out['pgh_enter']=await pg.evaluate(ST); await safeshot(pg,pre+'-qa023-pittsburgh.png'); print('QA-023',out['pgh_sugg'][:3],out['pgh_enter'],flush=True)
    await c.close()
    c,pg,log=await boot(b,eng,W,H)
    await typegq(pg,'Erie County, PA'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
    out['dbl_before']=await pg.evaluate(ST)
    x,y=W/2,H*0.55
    await pg.touchscreen.tap(x,y); await pg.wait_for_timeout(120); await pg.touchscreen.tap(x,y); await pg.wait_for_timeout(4000)
    out['dbl_after']=await pg.evaluate(ST); out['dbl_field']=await pg.evaluate("()=>{const g=document.getElementById('gq');return [g.value,g.placeholder]}")
    await safeshot(pg,pre+'-qa025-dbltap.png'); print('QA-025',out['dbl_before'],'->',out['dbl_after'],out['dbl_field'],flush=True)
    await c.close()
    # All States, '16>'24 line: points per row; '16>'20 labels
    c,pg,log=await boot(b,eng,W,H)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    # QA-018: tap OH row on its bar
    xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='OH'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+q.width*0.55,q.top+q.height/2]}")
    await pg.wait_for_timeout(500)
    if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(4000)
    out['qa018']=await pg.evaluate("()=>[window.__laInfo().lv,document.getElementById('crumbs').innerText]"); print('QA-018',out['qa018'],flush=True)
    if out['qa018'][0]!='states':
      await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(900)
    await pg.evaluate("()=>window.__ySet16(2)"); await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>{document.querySelector('#chartBox .cmain').click()}"); await pg.wait_for_timeout(800)
    await pg.evaluate("()=>{const b=document.querySelector('#chartBox .copts button[data-ch=line]'); b&&b.click()}"); await pg.wait_for_timeout(4000)
    out['line1624']=await pg.evaluate("()=>({chart:window.chartMode,ysl:window.__ysl.get(),rows:[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>/^(FL|PA|NY)\\b/.test(r.innerText.trim())).map(r=>({t:r.innerText.replace(/\\n/g,' | ').slice(0,90),pl:[...r.querySelectorAll('polyline,path')].map(p=>(p.getAttribute('points')||p.getAttribute('d')||'').trim().split(/\\s+|L/).length)}))})")
    await safeshot(pg,pre+'-qa066-line-16-24.png'); print('QA-066',json.dumps(out['line1624'])[:600],flush=True)
    await pg.evaluate("()=>window.__ySet16(1)"); await pg.wait_for_timeout(5000)
    out['lbl1620']=await pg.evaluate("()=>[...document.querySelectorAll('[aria-label]')].filter(e=>e.offsetParent&&/Trump|Harris|Biden|Clinton/.test(e.getAttribute('aria-label'))).map(e=>e.getAttribute('aria-label')+' ['+e.innerText.replace(/\\n/g,' ').trim()+']').slice(0,4)")
    print('QA-051',out['lbl1620'],flush=True)
    out['err']=log['pageerr'][:4]+[x for x in log['console'] if x.startswith('error')][:4]
    await c.close(); await b.close()
  json.dump(out,open(f'b1582p14-misc-{eng}-{W}.json','w'),indent=1)
asyncio.run(main())
