# usage: python3 tests/no-jump.py URL -- build 1565: the list's floating pieces (#laCands thumbnails, #bBack chevron, #laSort chip) never move or
# vanish on a tap: positions recorded on every animation frame for 1 s after each tap type (sort, %/#, year, type, chart menu, drill-in),
# iPad landscape 1024x576 and phone 390x844, time row open and closed. (1564 flashed the thumbnails up over the '20 label for a frame.)
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1] if len(sys.argv)>1 else "http://localhost:8843/v2/"; fails=0
def ck(n,ok,d=''):
  global fails
  print(('OK   ' if ok else 'FAIL ')+n,'' if ok else json.dumps(d)[:700]); fails+=0 if ok else 1
REC="""async(js)=>{const g=id=>{const e=document.getElementById(id); if(!e) return 'none'; const cs=getComputedStyle(e); if(e.hidden||cs.display==='none'||cs.visibility==='hidden') return 'hidden'; const r=e.getBoundingClientRect(); if(!r.width) return 'hidden'; return Math.round(r.left)+','+Math.round(r.top)};
 const snap=()=>['laCands','bBack','laSort'].map(g).join(' | '); const fr=[snap()]; let go=true; const loop=()=>{ fr.push(snap()); if(go) requestAnimationFrame(loop); }; requestAnimationFrame(loop);
 (new Function(js))(); await new Promise(r=>setTimeout(r,1000)); go=false; return fr}"""
TAPS=[('sort',"document.getElementById('laSort').click()"),
      ('num',"window.__setNum(document.querySelector('#bNum').textContent==='%'?'num':'pct')"),
      ('year',"const s=document.getElementById('yslider');s.value=s.value==s.max?s.min:s.max;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}))"),
      ('chartmenu',"document.querySelector('button.rbtn.cmain')&&document.querySelector('button.rbtn.cmain').click()"),
      ('chartclose',"document.body.click()"),
      ('generic',"document.getElementById('listView').click()")]
async def run(b,W,H,mob,timeopen):
    c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=mob,has_touch=mob); pg=await c.new_page()
    await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    if timeopen:
      await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
      await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(2500)
    T=f"{W}x{H} time {'open' if timeopen else 'closed'}"
    for name,js in TAPS:
      await pg.evaluate("()=>window.__quiet&&window.__quiet()")
      fr=await pg.evaluate(REC,js); await pg.wait_for_timeout(700)
      # stable = after the first settled frame, never a different position; compare against the final state
      fin=fr[-1]; bad=[x for x in fr[1:] if x!=fin and x!=fr[0]]; moved=len(set(fr[1:]))>1
      ck(f"{T} {name}: thumbnails/chevron/sort chip never jump ({len(fr)} frames, {fr[0]} -> {fin})",not bad and not (moved and fr[0]==fin),sorted(set(fr)))
    # drill-in (All States -> a state) last: the pieces may legitimately move once to the new list's place, but never through a third spot
    fr=await pg.evaluate(REC,"[...document.querySelectorAll('#listView .lvrow.la')].find(r=>r.querySelector('.nmx').textContent==='PA').click()")
    await pg.wait_for_timeout(5000); fin=await pg.evaluate("()=>['laCands','bBack','laSort'].map(id=>{const e=document.getElementById(id); if(!e) return 'none'; const cs=getComputedStyle(e); if(e.hidden||cs.display==='none'||cs.visibility==='hidden') return 'hidden'; const r=e.getBoundingClientRect(); if(!r.width) return 'hidden'; return Math.round(r.left)+','+Math.round(r.top)}).join(' | ')")
    seq=[x for i,x in enumerate(fr) if i==0 or x!=fr[i-1]]
    ck(f"{T} drill-in: no flash (only old -> new spots: {seq})",all(x in (fr[0],fin) or 'hidden' in x for x in seq) and len(seq)<=4,seq)
    await c.close()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,mob in ((1024,576,False),(390,844,True)):
      for to in (True,False): await run(b,W,H,mob,to)
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
