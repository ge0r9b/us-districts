# usage: python3 tests/line-two-point.py URL tag -- two-point line view: chart directly under the time filter, line endpoints exactly under the slider endpoints, thumbnails-only columns right below (2020 on the left label axis, 2024 under the '24 label), change values only, press bubbles; # and % modes, phone + desktop
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((430,800,'ph'),(1280,800,'dk')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bTime"); await pg.wait_for_timeout(500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='line'); x&&x.click();}"); await pg.wait_for_timeout(2500)
      for ch in ('line','pie'):
       if ch!='line': await pg.evaluate("c=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch===c); x&&x.click();}",ch); await pg.wait_for_timeout(1800)
       for mode in ('pct','num'):
         await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1500)
         r=await pg.evaluate("""(ch)=>{const x=document.querySelector('#cands .dlx'); if(!x) return {none:true}; const svg=x.querySelector('svg').getBoundingClientRect(); const circ=[...x.querySelectorAll(ch==='line'?'circle':'svg')].map(c=>{const b=c.getBoundingClientRect();return b.left+b.width/2});
           const dots=[...document.querySelectorAll('#ysl .tk i')].map(d=>{const b=d.getBoundingClientRect();return b.left+b.width/2}); const lbl=[...document.querySelectorAll('#ysl .ylb')].map(d=>{const b=d.getBoundingClientRect();return b.left+b.width/2});
           let cols; let ov=0; if(ch==='line'){ const im=[...x.querySelectorAll('img')].map(i=>i.getBoundingClientRect()), L=im.filter(r=>r.left+r.width/2<dots[0]), R=im.filter(r=>r.left+r.width/2>dots[1]); cols=[L[0].left+L[0].width/2,R[0].left+R[0].width/2]; const cy=[...x.querySelectorAll('circle')].map(c=>{const b=c.getBoundingClientRect();return [b.left+b.width/2,b.top+b.height/2]}); ov=0; [L,R].forEach(col=>{ col.sort((a,b)=>a.top-b.top); if(col.length==2&&col[1].top<col[0].bottom) ov++; }); const tx=[...x.querySelectorAll('text')].map(e=>e.getBoundingClientRect()); tx.forEach(a=>im.forEach(b=>{ if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top) ov++; })); const near=L.every((r,i)=>true); } else { cols=[...x.querySelectorAll('.dlc')].map(c=>{const i=c.querySelector('img').getBoundingClientRect();return i.left+i.width/2}); } const tb=document.getElementById('barTime').getBoundingClientRect(); const rail=document.querySelector('.rail').getBoundingClientRect().left;
           const maxR=Math.max(...[...x.querySelectorAll('text,img')].map(e=>e.getBoundingClientRect().right));
           return {top:Math.round(svg.top-tb.bottom),c0:circ[0],c1:circ[circ.length-1],d0:dots[0],d1:dots[dots.length-1],k0:cols[0],k1:cols[1],l0:lbl[0],l1:lbl[1],ov:ov,txt:x.innerText.replace(/\\s+/g,' '),maxR,rail,others:[...document.querySelectorAll('#cands > *')].filter(e=>e!==x&&getComputedStyle(e).display!=='none').length}}""",ch)
         ok=(not r.get('none')) and (ch=='pie' or (abs(r['c0']-r['d0'])<=1.5 and abs(r['c1']-r['d1'])<=1.5)) and (abs(r['k0']-r['l0'])<=1.5 and r['k1']>r['d1']+20 and r['ov']==0 if ch=='line' else abs(r['k0']-r['d0'])<=1.5 and abs(r['k1']-r['d1'])<=1.5) and r['top']<=16 and r['maxR']<=r['rail'] and r['others']==0 and not re.search(r'Republican|Democratic|20\d\d|\d{2},\d{3}',r['txt'])
         fails+=0 if ok else 1; print(t,ch,mode,'OK' if ok else 'FAIL',json.dumps(r)[:380],flush=True)
         await pg.screenshot(path=f"/workspace/shots/ln-{tag}-{t}-{ch}-{mode}.png")
         if mode=='num':
           await pg.evaluate("()=>document.querySelector('#cands .dlx g, #cands .dlx path').dispatchEvent(new MouseEvent('click',{bubbles:true}))"); await pg.wait_for_timeout(300)
           bt=await pg.evaluate("()=>{const e=document.getElementById('partyBub');return e&&e.textContent}"); ok=bool(bt) and len(bt)<=32 and re.search(r'\d',bt); fails+=0 if ok else 1; print(t,'line bubble','OK' if ok else 'FAIL',bt)
           await pg.evaluate("()=>document.querySelector('#cands .dlx img').click()"); await pg.wait_for_timeout(300)
           bt=await pg.evaluate("()=>{const e=document.getElementById('partyBub');return e&&e.textContent}"); ok=bool(bt) and ('Trump' in bt or 'Biden' in bt or 'Harris' in bt); fails+=0 if ok else 1; print(t,'thumb bubble','OK' if ok else 'FAIL',bt)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
