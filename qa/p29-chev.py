# pass 29: the back chevron left on All States after a DC address search from PA > Philadelphia townships: what is it, what does it do?
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
src=open('p28-addr.py').read(); exec(src[src.index('NMXY='):src.index('ADDR=')])
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
CH="""()=>{const els=[...document.querySelectorAll('*')].filter(e=>{if(!e.offsetParent&&getComputedStyle(e).position!=='fixed')return false;const r=e.getBoundingClientRect();return r.width>10&&r.width<60&&r.left<40&&r.top>110&&r.top<160&&(e.tagName==='BUTTON'||e.getAttribute('role')==='button'||/back/i.test(e.className+' '+e.id))});
 const bb=document.getElementById('bBack');if(bb&&bb.getBoundingClientRect().width&&!els.includes(bb))els.unshift(bb);return els.map(e=>{const r=e.getBoundingClientRect();return {tag:e.tagName,id:e.id,cls:String(e.className).slice(0,60),aria:e.getAttribute('aria-label'),box:[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}})}"""
async def main():
  eng=sys.argv[1]; W,H=390,844; R={'eng':eng}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for sc in ['tapdc_after_phila','addr_phila']:
      c,pg,log=await ctx(b,W,H,True,eng)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
      await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3500)
      await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Philadelphia'))); await pg.wait_for_timeout(3500)
      r={'phila_chev':await pg.evaluate(CH)}
      if sc=='addr_phila':
        await pg.touchscreen.tap(*(await center(pg,"#gq"))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
        await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
      else:
        # Back twice to All States, then tap DC: the normal way to DC from the same start
        for _ in range(2):
          xy=await center(pg,'#bBack')
          if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3000)
        await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'DC'))); await pg.wait_for_timeout(4000)
      r['after']=await pg.evaluate(ST); r['chev']=await pg.evaluate(CH)
      await pg.screenshot(path=f"../shots/b{R['build'][-4:]}p29-{eng[:2]}-390-chev-{sc}.png")
      if r['chev']:
        bx=r['chev'][0]['box']; await pg.touchscreen.tap(bx[0]+bx[2]/2,bx[1]+bx[3]/2); await pg.wait_for_timeout(4000)
        r['after_chev_tap']=await pg.evaluate(ST); r['chev2']=await pg.evaluate(CH)
        await pg.screenshot(path=f"../shots/b{R['build'][-4:]}p29-{eng[:2]}-390-chev-{sc}-tapped.png")
      r['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')]
      R[sc]=r; print(sc,json.dumps(r),flush=True); await c.close()
    await b.close()
  json.dump(R,open(f"b{R.get('build','0000')[-4:]}p29-chev-{eng}-390.json",'w'),indent=1)
asyncio.run(main())
