# usage: python3 tests/list-all-modes.py URL tag -- list-all: 'List all countries' label, delta mode (change bars + consistent sort), # vs % pie (real toggle), precinct level via the institution list
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
def chk(name,ok,info=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',name,info,flush=True)
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>r.innerText.replace(/\\n/g,' | '))"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((430,900,'ph'),(1280,800,'dk')):
      pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      sh=lambda n: pg.screenshot(path=f"/workspace/shots/lam-{tag}-{t}-{n}.png")
      # --- all countries
      await pg.evaluate("()=>window.__allPick()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
      lab=await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); return l&&l.innerText.trim()}"); chk(t+' countries label',lab=='List all countries',lab)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3500)
      rows=await pg.evaluate(ROWS); nC=await pg.evaluate("()=>(window.COUNTRIES||[]).length")
      chk(t+' countries rows',len(rows)==nC and len(rows)>100,f'{len(rows)}/{nC} first={rows[:2]}'); await sh('countries')
      await pg.evaluate("()=>window.__laExit()"); await pg.wait_for_timeout(500)
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      # --- states, delta, bars
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='bar'); x&&x.click();}"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3500)
      await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(3000)
      info=await pg.evaluate("()=>{const lv=document.getElementById('listView'); const rows=[...lv.querySelectorAll('.lvrow.la')]; const g=(r,k)=>{const x=[...r.querySelectorAll('.cbr')].find(c=>c.querySelector('.cbl').textContent===k); return x?x.querySelector('.cbv').textContent:null}; return {n:rows.length,dv:lv.querySelectorAll('.cbt.dv').length,rep:rows.map(r=>g(r,'Republican')),dem:rows.map(r=>g(r,'Democratic')),names:rows.map(r=>r.querySelector('b').textContent)}}")
      num=lambda s: float(re.sub(r'[^0-9.+-]','',s.replace('−','-'))) if s else None
      rep=[num(x) for x in info['rep']]
      chk(t+' delta rows+bars',info['n']>=51 and info['dv']>=51*2,f"rows={info['n']} dvbars={info['dv']} sample={info['rep'][:3]}")
      rep=[x for x in rep if x is not None]; desc=all(rep[i]>=rep[i+1]-1e-9 for i in range(len(rep)-1))
      chk(t+' delta sort desc by Republican shift',desc,f'{rep[:4]}..{rep[-3:]}'); await sh('delta-desc')
      await pg.evaluate("()=>document.getElementById('laSort').click()"); await pg.wait_for_timeout(400)
      await pg.evaluate("()=>[...document.querySelectorAll('#laSortPop button')][1].click()"); await pg.wait_for_timeout(1200)
      rep2=[num(x) for x in await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>{const x=[...r.querySelectorAll('.cbr')].find(c=>c.querySelector('.cbl').textContent==='Republican'); return x&&x.querySelector('.cbv').textContent})")]
      rep2=[x for x in rep2 if x is not None]; rep=[x for x in rep if x is not None]; asc=all(rep2[i]<=rep2[i+1]+1e-9 for i in range(len(rep2)-1)); chk(t+' delta sort asc',asc and rep2[0]==min(rep),f'{rep2[:3]}'); await sh('delta-asc')
      # --- pie # and % with the real toggle (single year and delta)
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='pie'); x&&x.click();}"); await pg.wait_for_timeout(800)
      async def tog(m):
        await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(500)
        await pg.evaluate("(m)=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()===m); b&&b.click();}",m); await pg.wait_for_timeout(1500)
      for rng in ('one','delta'):
        if rng=='delta': await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(1500)
        for m,want in (('#','num'),('%','pct')):
          await tog(m); mode=await pg.evaluate("()=>window.__numMode()")
          caps=await pg.evaluate("()=>[...document.querySelectorAll('.cpanel svg text')].map(e=>e.textContent)")
          txt=' '.join(caps); okc=len(caps)==(4 if rng=='delta' else 2) and ((all(c.endswith('%') for c in caps)) if want=='pct' else (not any('%' in c for c in caps) and all(re.search(r'\d',c) for c in caps)))
          chk(f'{t} pie {rng} {m}',mode==want and okc,f'mode={mode} caps={caps[:3]}'); await sh(f'pie-{rng}-{want}')
      print(er[:2]); await pg.close()
      # --- precinct level via the institution list (US House district -> precincts)
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      async def opn():
        await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(2000)
      async def clk(sel,tx):
        r=await pg.evaluate("([s,t])=>{const l=[...document.querySelectorAll(s)].find(l=>l.innerText.trim().includes(t)); if(l){l.click(); return true} return false}",[sel,tx]); await pg.wait_for_timeout(3500); return r
      await opn(); await clk('#orgTypes li','US House districts'); await opn(); await clk('.foldlist li','Pennsylvania'); await opn()
      lab=await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); return l&&l.innerText.trim()}"); chk(t+' districts label',lab=='List all US House districts',lab)
      await pg.locator('#sheet .foldlist li',has_text='District 03').first.locator('.go').click(); await pg.wait_for_timeout(5000); await opn()
      lab=await pg.evaluate("()=>{const l=document.querySelector('li.la-row'); return l&&l.innerText.trim()}"); chk(t+' precinct label',lab=='List all precincts',lab)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(8000)
      r=await pg.evaluate("()=>[document.querySelectorAll('#listView .lvrow.la').length,window.__LA.title]"); chk(t+' precinct rows',r[0]>100 and 'District 03' in r[1] and not re.search(r'\d\.\d{3}',r[1]),str(r)); await sh('precincts')
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
