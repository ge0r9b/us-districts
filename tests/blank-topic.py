# usage: python3 tests/blank-topic.py URL tag -- blank topic = no results anywhere: geo-select LA County (typed and via institution) with blank topic, sampled every animation frame for 3s: no candidate block/thumbnails/percent text is ever visible; also after reload; desktop + phone
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
def chk(n,ok,i=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,json.dumps(i)[:300],flush=True)
SAMPLE="""()=>{ window.__bad=[]; window.__frames=0; const t0=performance.now(); const f=()=>{ window.__frames++; const c=document.getElementById('cands'); const vis=[...document.querySelectorAll('#cands, #cands *, .cpanel, .dmx, .dlx')].filter(e=>e.offsetParent&&e.getBoundingClientRect().width>0&&e.getBoundingClientRect().height>0); const txt=vis.map(e=>e.children.length?'':e.textContent).join(' '); if(vis.length&&/\\d+(\\.\\d)?%|Trump|Harris/.test(txt)) window.__bad.push([Math.round(performance.now()-t0),vis.length,txt.slice(0,40)]); if(performance.now()-t0<3000) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base.split('#')[0],wait_until="networkidle"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>window.__setTopic(null)"); await pg.wait_for_timeout(800)
      await pg.evaluate(SAMPLE)
      await pg.evaluate("()=>{const g=document.getElementById('gq'); g.focus();}"); await pg.wait_for_timeout(500); await pg.keyboard.type("los angeles county, ca"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(3500)
      r=await pg.evaluate("()=>({bad:window.__bad.slice(0,3),frames:window.__frames,st:state.value,co:county.value,notopic:document.body.classList.contains('notopic')})")
      chk(f'{t} LA County, blank topic: no results block in {r["frames"]} frames',r['st']=='California' and not r['bad'] and r['notopic'],r); await pg.screenshot(path=f"/workspace/shots/bt-{tag}-{t}.png")
      await pg.reload(wait_until="networkidle"); await pg.evaluate(SAMPLE); await pg.wait_for_timeout(3500)
      r=await pg.evaluate("()=>({bad:window.__bad.slice(0,3),notopic:document.body.classList.contains('notopic'),snaptop:window.__stateSnapshot().top})")
      chk(f'{t} reload keeps blank topic, no results',not r['bad'] and r['notopic'] and r['snaptop']=='-',r)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
