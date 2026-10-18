# Build 1573 (user on 1571): pie view shows only the thumbnails, stacked top-left in rank order (winner first), no names or numbers;
# a tap shows the full name + value in the standard bubble; nothing overlaps the pie at 320 / 390 / 1024. President / Massachusetts / 2024 / # / pie.
import asyncio,sys,json,math
from playwright.async_api import async_playwright
U=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"
F=[]
def ck(c,m,x=None): print(("OK   " if c else "FAIL ")+m+("" if c else " "+json.dumps(x)[:400])); (None if c else F.append(m))
PICK="""async(k)=>{const m=document.querySelector('button.rbtn.cmain');if(window.chartMode===k)return;m.click();await new Promise(r=>setTimeout(r,300));const b=[...document.querySelectorAll('.copts button')].find(b=>b.dataset.ch===k);if(b)b.click();else if(m.dataset.ch===k)m.click()}"""
GEO="""()=>{const sv=[...document.querySelectorAll('.cpanel svg')].find(e=>e.getBoundingClientRect().width>60);if(!sv)return null;const q=sv.getBoundingClientRect();
 const th=[...document.querySelectorAll('#cands .cand')].filter(b=>b.offsetParent).map(b=>{const r=b.getBoundingClientRect();return {t:b.title,r:[r.left,r.top,r.right,r.bottom]}});
 const txt=[...document.querySelectorAll('#cands .cand .cn, #cands .cand .cs, #cands .cand .cpt')].filter(e=>e.offsetParent&&e.getBoundingClientRect().width>0).map(e=>e.textContent);
 const btn=[...document.querySelectorAll('button.rbtn')].filter(b=>b.offsetParent).map(b=>{const r=b.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]});
 return {pie:[q.left+q.width/2,q.top+q.height/2,q.width/2],th,txt,btn}}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in ((320,640),(390,844),(1024,768)):
      c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=1,is_mobile=W<600,has_touch=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e))); T=f"{W}x{H}:"
      await pg.goto(U,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Massachusetts';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(5000)
      await pg.evaluate("()=>window.__setNum('num')"); await pg.wait_for_timeout(500)
      await pg.evaluate(PICK,'pie'); await pg.wait_for_timeout(2500)
      g=await pg.evaluate(GEO)
      ck(g and len(g['th'])==2,T+" pie + two thumbnails",g)
      if not g: await c.close(); continue
      ck(not g['txt'],T+" no names / numbers beside the thumbnails",g['txt'])
      ck(g['th'][0]['t'].startswith('Kamala Harris') and g['th'][0]['r'][1]<g['th'][1]['r'][1],T+" rank order, winner on top (Harris in MA)",[x['t'] for x in g['th']])
      cx,cy,R=g['pie']
      def hit(r): nx=min(max(cx,r[0]),r[2]); ny=min(max(cy,r[1]),r[3]); return math.hypot(nx-cx,ny-cy)<R-1
      ims=await pg.evaluate("()=>[...document.querySelectorAll('#cands .cand img')].filter(i=>i.offsetParent).map(i=>{const r=i.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]})")
      ck(not any(hit(r) for r in ims),T+" thumbnail photos don't overlap the pie (build 1585: the pie sits right of the thumbnail column)",[g['pie'],ims])
      ck(not any(hit(r) for r in g['btn']),T+" buttons don't overlap the pie",[g['pie'],g['btn']])
      await pg.evaluate("()=>[...document.querySelectorAll('#cands .cand')].find(b=>b.offsetParent).click()"); await pg.wait_for_timeout(300)
      bb=await pg.evaluate("()=>{const b=document.getElementById('iconBub');return b?b.textContent:null}")
      ck(bb=='Kamala Harris',T+" tap shows the name in the white bubble (build 1585: name only; the chart shows the numbers)",bb)
      await pg.screenshot(path=f'/workspace/pie-thumbs-{W}.png')
      ck(not er,T+" no page errors",er[:2]); await c.close()
    await b.close()
asyncio.run(main()); print("FAILS",len(F)); sys.exit(1 if F else 0)
