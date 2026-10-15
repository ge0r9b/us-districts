# usage: python3 tests/district-ctx.py URL tag -- district-type button group is data-driven per country: shown for the US, hidden (slot kept, no layout shift) for Canada selected via the geo field or the institution list, any district layer reset to default, group returns in the US; phone + desktop
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
S="()=>{const b=document.getElementById('bLyr'),r=b.getBoundingClientRect(); return {w:window.__W&&window.__W(),nodist:document.body.classList.contains('nodist'),vis:getComputedStyle(b).visibility,top:Math.round(r.top),lt:window.__stateSnapshot().lt,types:window.__districtTypes()}}"
def chk(n,ok,i=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,json.dumps(i)[:300],flush=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base.split('#')[0],wait_until="networkidle"); await pg.wait_for_timeout(3500)
      s0=await pg.evaluate(S); chk(f'{t} US: group visible with 4 types',s0['vis']=='visible' and not s0['nodist'] and len(s0['types'])==4,s0)
      await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=senate]'); b&&b.click();}"); await pg.wait_for_timeout(2000)
      # Canada via geo field
      await pg.evaluate("()=>{const g=document.getElementById('gq'); g.focus();}"); await pg.wait_for_timeout(400); await pg.keyboard.type("canada"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
      s1=await pg.evaluate(S); chk(f'{t} Canada (geo field): group hidden, layer reset, slot kept',s1['w']=='ca' and s1['nodist'] and s1['vis']=='hidden' and s1['lt']!='senate' and s1['top']==s0['top'],s1); await pg.screenshot(path=f"/workspace/shots/dc-{tag}-{t}-canada.png")
      await pg.evaluate("()=>window.__worldExit&&window.__worldExit()"); await pg.wait_for_timeout(3000)
      s2=await pg.evaluate(S); chk(f'{t} back to US: group returns',s2['vis']=='visible' and not s2['nodist'] and len(s2['types'])==4,s2); await pg.screenshot(path=f"/workspace/shots/dc-{tag}-{t}-us.png")
      # Canada via institution list
      await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=ushouse]'); b&&b.click();}"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>window.__orgCountry&&window.__orgCountry('ca')"); await pg.wait_for_timeout(3500)
      s3=await pg.evaluate(S); chk(f'{t} Canada (institution): group hidden, layer reset',s3['w']=='ca' and s3['nodist'] and s3['lt']!='ushouse',s3)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
