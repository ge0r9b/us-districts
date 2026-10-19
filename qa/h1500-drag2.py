# hourly 3PM (1617) QA-108 retest, from p36-drag2: knob drag '24 -> '16 at 1024x768 with each input kind (mouse vs touch) to tell input from engine
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def run(p,eng,kind):
  b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,1024,768,False,eng)
  await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
  await typegq(pg,'Pennsylvania'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
  await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1200)
  kn=await pg.evaluate("()=>{const r=document.querySelector('.kn.a').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}")
  t=await pg.evaluate("()=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();return [r.left+52,r.top+r.height/2]}")
  if kind=='mouse':
    await pg.mouse.move(*kn); await pg.mouse.down()
    for s in range(1,13): await pg.mouse.move(kn[0]+(t[0]-kn[0])*s/12,kn[1]); await pg.wait_for_timeout(25)
    await pg.mouse.up()
  elif kind=='cdptouch':
    cdp=await c.new_cdp_session(pg); await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':kn[0],'y':kn[1],'id':1}]})
    for s in range(1,13): await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':kn[0]+(t[0]-kn[0])*s/12,'y':kn[1],'id':1}]}); await pg.wait_for_timeout(25)
    await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
  else:  # synthetic touch pointer events
    await pg.evaluate("""([a,b,y])=>new Promise(res=>{const w=document.querySelector('.kn.a').parentElement;const tg=document.elementFromPoint(a,y)||w;const ev=(t,cx)=>tg.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:7,pointerType:'touch',isPrimary:true,clientX:cx,clientY:y}));
      ev('pointerdown',a);let k=0;const f=()=>{k++;ev('pointermove',a+(b-a)*k/12);if(k<12)requestAnimationFrame(f);else{ev('pointerup',b);res(1)}};requestAnimationFrame(f)})""",[kn[0],t[0],kn[1]])
  await pg.wait_for_timeout(3000)
  r={'ysl':await pg.evaluate("()=>window.__ysl.get()"),'th':await pg.evaluate("()=>[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' '))"),'err':log['pageerr'],'build':await pg.evaluate('window.BUILD')}
  await safeshot(pg,f'shotsh1500/b1617h-{eng[:2]}-1024x768-drag2-{kind}.png'); await b.close(); return r
async def main():
  out={}
  async with async_playwright() as p:
    for eng,kind in [('chromium','mouse'),('chromium','cdptouch'),('chromium','ptouch'),('webkit','mouse'),('webkit','ptouch')]:
      out[f'{eng}-{kind}']=await run(p,eng,kind); print(eng,kind,out[f'{eng}-{kind}'],flush=True)
  json.dump(out,open('b1617h1500-drag2.json','w'),indent=1)
asyncio.run(main())
