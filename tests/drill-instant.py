# Build 1567: a drill-in tap (state row -> counties, county row -> townships) shows the target list at once: cached rows of the
# target (visited before) or skeleton rows, painted within 150 ms of the tap (4x CPU throttle); the thumbnails stay hidden until the
# new list renders, then appear in the same frame as the back chevron, already in their final spot; back still returns.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
TAP="""async(sel)=>{const lv=document.getElementById('listView');let t0,res;const done=new Promise(r=>res=r);
const mo=new MutationObserver(()=>{mo.disconnect();requestAnimationFrame(()=>{const c=new MessageChannel();c.port1.onmessage=()=>res(performance.now()-t0);c.port2.postMessage(0)})});
mo.observe(lv,{subtree:true,childList:true});const fr=[];let go=1;const q=s=>{const e=document.querySelector(s);if(!e)return 'hid';const r=e.getBoundingClientRect();return r.height>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'?Math.round(r.left)+','+Math.round(r.top):'hid'};
const tick=()=>{fr.push(q('#laCands')+'|'+q('#bBack'));if(go)requestAnimationFrame(tick)};
const row=[...lv.querySelectorAll('.lvrow.la')].find(r=>r.querySelector('.nmx').textContent===sel)||lv.querySelectorAll('.lvrow.la')[4];
t0=performance.now();tick();row.click();const g=lv.querySelector('.lvgrid');const sk={skel:g.classList.contains('skel'),skrows:g.querySelectorAll('.lvskel').length,rows:g.children.length,hid:document.body.classList.contains('laskel')};
const ms=await done;await new Promise(r=>setTimeout(r,9000));go=0;const seq=fr.filter((x,i)=>i==0||x!==fr[i-1]);return {ms:Math.round(ms),sk,seq,n:lv.querySelectorAll('.lvrow.la').length,crumb:document.getElementById('crumbs').textContent}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,mob in ((390,844,True),(1024,576,False)):
      c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=mob,has_touch=True); pg=await c.new_page()
      er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(6000)
      cdp=await c.new_cdp_session(pg)
      async def drill(sel,tag,cached=False):
        await cdp.send("Emulation.setCPUThrottlingRate",{"rate":4}); r=await pg.evaluate(TAP,sel); await cdp.send("Emulation.setCPUThrottlingRate",{"rate":1})
        t=f"{W}x{H} {tag}"
        ck(r['ms']<150,f"{t}: first visible response {r['ms']}ms (<150, 4x CPU)",r['ms'])
        ck(r['sk']['skel'] and r['sk']['hid'] and (r['sk']['skrows']==0 if cached else r['sk']['skrows']>0) and r['sk']['rows']>0,f"{t}: {'cached rows' if cached else 'skeleton rows'} shown at once, thumbnails held back",r['sk'])
        seq=r['seq']; k=next((i for i,x in enumerate(seq) if x.startswith('hid')),len(seq)); first=next((x for x in seq[k:] if not x.startswith('hid')),None); mid=[x for x in seq[k:] if x.startswith('hid') and x!='hid|hid']
        ck(first is not None and first==seq[-1] and first.split('|')[1]!='hid' and not mid,f"{t}: thumbnails appear together with the chevron, straight in their final spot",seq)
        ck(r['n']>3,f"{t}: new list rendered ({r['n']} rows, {r['crumb']})",r)
        return r
      await drill('PA','All States -> PA (skeleton)')
      await drill(None,'PA -> county townships (skeleton)')
      await pg.evaluate("()=>history.back()"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>history.back()"); await pg.wait_for_timeout(6000)
      cr=await pg.evaluate("()=>document.getElementById('crumbs').textContent"); ck('All States' in cr,f"{W}x{H}: back twice returns to All States",cr)
      await drill('PA','All States -> PA again (cached rows)',True)
      ck(not er,f"{W}x{H}: no page errors",er[:2]); await c.close()
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
