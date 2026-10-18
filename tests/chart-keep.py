# Build 1571: the chosen chart type never changes when the timeline moves (user feedback on 1569).
# President / United States: pie at '20 -> drag to the '20-'24 range -> still pie, showing 2024 (Harris / Trump);
# the chart menu still offers bar and line; line only when picked; the type survives slider moves and a reload.
import asyncio,sys,json
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
ST="""()=>{const m=document.querySelector('button.rbtn.cmain');const pie=[...document.querySelectorAll('.cpanel .cpie1 svg, .cwide.pieonly svg')].filter(e=>e.getBoundingClientRect().width>40);
 const names=[...document.querySelectorAll('[data-party]')].filter(e=>e.offsetParent).map(e=>e.getAttribute('data-party')).join(' ');
 return {ch:window.chartMode,btn:m&&m.dataset.ch,ym:ym(),raw:window.__ymRaw(),pie:pie.length,harris:/Harris/.test(names+(pie[0]?pie[0].outerHTML:'')),biden:/Biden/.test(pie[0]?pie[0].outerHTML:''),slider:+document.getElementById('yslider').value}}"""
OPTS="""async()=>{document.querySelector('button.rbtn.cmain').click();await new Promise(r=>setTimeout(r,300));const o=[...document.querySelectorAll('.copts button')].map(b=>b.dataset.ch);document.getElementById('chartDim').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));return o}"""
PICK="""async(k)=>{const m=document.querySelector('button.rbtn.cmain');if(m.dataset.ch===k&&window.chartMode===k)return 'same';m.click();await new Promise(r=>setTimeout(r,300));const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch===k);if(b){b.click();return 'opt'}if(m.dataset.ch===k){m.click();return 'main'}return 'none'}"""
SL="(v)=>{const s=document.getElementById('yslider');s.value=v;s.dispatchEvent(new Event('input',{bubbles:true}))}"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in ((390,844),(1024,768)):
      c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=1,is_mobile=W<600,has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)))
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500); T=f"{W}x{H}:"
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.evaluate("()=>document.getElementById('bTime').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate(SL,0); await pg.wait_for_timeout(1200)
      await pg.evaluate(PICK,'pie'); await pg.wait_for_timeout(2000)
      s=await pg.evaluate(ST); ck(s['ch']=='pie' and s['pie']>=1 and s['ym']=='2020',T+" pie at '20",s)
      await pg.evaluate(SL,1); await pg.wait_for_timeout(2000)
      s=await pg.evaluate(ST); ck(s['ch']=='bar' and s['btn']=='bar' and s['pie']==0 and s['raw']=='delta',T+" range '20-'24: pie isn't offered in a range -> bar (build 1577)",s)
      await pg.screenshot(path=f'/workspace/chart-keep-{W}.png')
      o=await pg.evaluate(OPTS); ck(set(o)=={'line'},T+" menu in range offers line (bar on the main button), no pie",o)
      await pg.evaluate(SL,2); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(s['ch']=='pie' and s['ym']=='2024',T+" '24: one year again -> pie comes back",s)
      await pg.evaluate(PICK,'bar'); await pg.wait_for_timeout(1200); await pg.evaluate(SL,1); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(s['ch']=='bar' and s['ym']=='delta',T+" bar stays bar in the range (change view)",s)
      await pg.evaluate(SL,0); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(s['ch']=='bar',T+" bar stays bar at '20",s)
      await pg.evaluate(SL,1); await pg.wait_for_timeout(1200)
      await pg.evaluate(PICK,'line'); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(s['ch']=='line' and s['raw']=='delta',T+" line picked in the range",s)
      await pg.evaluate(SL,0); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(s['ch']=='bar',T+" one year: no line -> bar",s)
      await pg.evaluate(SL,1); await pg.wait_for_timeout(1500); s=await pg.evaluate(ST); ck(s['ch']=='line',T+" range again: line comes back",s)
      o=await pg.evaluate(OPTS); ck('pie' not in o,T+" range: pie not in the menu",o)
      await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(300)
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
      s=await pg.evaluate(ST); ck(s['ch']=='line' and s['raw']=='delta',T+" reload keeps line and the range",s)
      ck(not er,T+" no page errors",er[:2]); await c.close()
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
