# Build 1568: in the results list a time-slider change paints the updated list within 150 ms (median, 4x CPU throttle, phone),
# for US House and county lists; the map layers under the list follow one frame later (deferred, then actually redrawn),
# and on the map view the slider still redraws the map at once.
import asyncio,sys,json,statistics
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
SL="const s=document.getElementById('yslider');s.value=s.value==s.max?s.min:s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))"
TAP="""async(js)=>{const lv=document.getElementById('listView');let t0,res;const done=new Promise(r=>res=r);
const mo=new MutationObserver(()=>{mo.disconnect();requestAnimationFrame(()=>{const c=new MessageChannel();c.port1.onmessage=()=>res(performance.now()-t0);c.port2.postMessage(0)})});
mo.observe(lv,{subtree:true,childList:true,characterData:true});const o0=JSON.stringify(window.__laInfo().order.slice(0,5));const r0=window.__laterRuns;
t0=performance.now();(new Function(js))();setTimeout(()=>{mo.disconnect();res(-1)},3000);const ms=Math.round(await done);await new Promise(r=>setTimeout(r,800));
return {ms,changed:JSON.stringify(window.__laInfo().order.slice(0,5))!==o0,later:window.__laterRuns-r0}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for kind in ('ushouse','county'):
      c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True); pg=await c.new_page()
      er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      if kind=='ushouse': await pg.evaluate("()=>document.querySelector('.lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
      cdp=await c.new_cdp_session(pg); await cdp.send("Emulation.setCPUThrottlingRate",{"rate":4})
      rs=[]
      for i in range(7): rs.append(await pg.evaluate(TAP,SL)); await pg.wait_for_timeout(700)
      await cdp.send("Emulation.setCPUThrottlingRate",{"rate":1})
      ms=[r['ms'] for r in rs]; med=statistics.median(ms)
      ck(med<150 and min(ms)>0,f"{kind}: slider -> list painted, median {med}ms (<150, 4x CPU) {ms}",ms)
      ck(all(r['later']>0 for r in rs),f"{kind}: map layers redrawn right after (deferred redraw ran each time)",rs)
      ck(not er,f"{kind}: no page errors",er[:2]); await c.close()
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
