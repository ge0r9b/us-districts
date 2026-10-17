# usage: python3 tests/list-all-modes.py URL tag -- (refreshed for build 1548: clean storage per section, candidate-share % sort) list-all: 'List all countries' label, delta mode (change bars + consistent sort), # vs % pie (real toggle), precinct level via the institution list
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
    async def newpage(W,H):
      # the app restores the last view from localStorage (usd.state); every section must start from a clean US view
      c=await b.new_context(viewport={"width":W,"height":H}); await c.add_init_script("try{localStorage.clear()}catch(e){}"); return await c.new_page()
    for W,H,t in((430,900,'ph'),(1280,800,'dk')):
      pg=await newpage(W,H); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
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
      info=await pg.evaluate("()=>{const lv=document.getElementById('listView'); const rows=[...lv.querySelectorAll('.lvrow.la')]; return {n:rows.length,dv:lv.querySelectorAll('.sbw.dl').length,names:rows.map(r=>r.querySelector('b').textContent)}}")
      chk(t+' delta rows+scaled delta bars (build 1528+ layout)',info['n']>=51 and info['dv']>=51,f"rows={info['n']} dvbars={info['dv']}")
      ordr=lambda: pg.evaluate("()=>window.__LA.order")
      o=await ordr(); vs=[x[1] for x in o if x[1] is not None]
      chk(t+' delta sort desc by |net change| as displayed (t272)',all(vs[i]>=vs[i+1] for i in range(len(vs)-1)) and len(vs)>=50,f'{o[:2]}..{o[-2:]}'); await sh('delta-desc')
      await pg.evaluate("()=>{ if(window.__laInfo().sort!=='asc') document.getElementById('laSort').click(); }"); await pg.wait_for_timeout(1200)
      o2=await ordr(); vs2=[x[1] for x in o2 if x[1] is not None]
      chk(t+' delta sort asc',all(vs2[i]<=vs2[i+1] for i in range(len(vs2)-1)),f'{o2[:2]}'); await sh('delta-asc')
      # single year, # and %: California first / Wyoming+DC last on high-to-low, reverse on low-to-high
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3500)
      async def tg(m):
        await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(500)
        await pg.evaluate("(m)=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()===m); b&&b.click();}",m); await pg.wait_for_timeout(1500)
      async def setsort(i):
        await pg.evaluate("(i)=>{ const w=i===0?'desc':'asc'; if(window.__laInfo().sort!==w) document.getElementById('laSort').click(); }",i); await pg.wait_for_timeout(1200)
      # '#': raw votes (California first, Wyoming/DC last); '%' (build 1546+): share of the selected candidate(s) = leader's share with all on (DC first, closest states such as Wisconsin last)
      for m in ('#','%'):
        await tg(m); await setsort(0); oo=await ordr(); o=[x[0] for x in oo]; v=[x[1] for x in oo if x[1] is not None]
        mono=all(v[i]>=v[i+1] for i in range(len(v)-1)) and len(v)>=50
        if m=='#': ok=o[0]=='California' and o[1]=='Texas' and 'Wyoming' in o[-4:] and 'District of Columbia' in o[-4:]
        else: ok=o[0]=='District of Columbia' and 'Wisconsin' in o[-4:] and 'Michigan' in o[-6:]
        chk(f'{t} sort high-low {m}',ok and mono,f'{oo[:3]}..{oo[-3:]}')
        await sh('sort-desc-'+('num' if m=='#' else 'pct'))
        await setsort(1); oo=await ordr(); o=[x[0] for x in oo]; v=[x[1] for x in oo if x[1] is not None]
        mono=all(v[i]<=v[i+1] for i in range(len(v)-1)) and len(v)>=50
        if m=='#': ok=o[-1]=='California' and o[-2]=='Texas' and 'Wyoming' in o[:4] and 'District of Columbia' in o[:4]
        else: ok=o[-1]=='District of Columbia' and 'Wisconsin' in o[:4]
        chk(f'{t} sort low-high {m}',ok and mono,f'{oo[:3]}..{oo[-3:]}'); await setsort(0)
      # --- pie # and % with the real toggle (single year and delta)
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='pie'); x&&x.click();}"); await pg.wait_for_timeout(800)
      async def tog(m):
        await pg.evaluate("()=>document.getElementById('bNum').click()"); await pg.wait_for_timeout(500)
        await pg.evaluate("(m)=>{const b=[...document.querySelectorAll('button')].find(b=>b.offsetParent&&b.textContent.trim()===m); b&&b.click();}",m); await pg.wait_for_timeout(1500)
      for rng in ('one',):  # delta pie ring removed (t251-t254): pie is single-point only
        if rng=='delta': await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(1500)
        for m,want in (('#','num'),('%','pct')):
          await tog(m); mode=await pg.evaluate("()=>window.__numMode()")
          caps=await pg.evaluate("()=>[...document.querySelectorAll('.cpanel svg text')].map(e=>e.textContent)")
          txt=' '.join(caps); okc=len(caps)==(4 if rng=='delta' else 2) and ((all(c.endswith('%') for c in caps)) if want=='pct' else (not any('%' in c for c in caps) and all(re.search(r'\d',c) for c in caps)))
          chk(f'{t} pie {rng} {m}',mode==want and okc,f'mode={mode} caps={caps[:3]}'); await sh(f'pie-{rng}-{want}')
      print(er[:2]); await pg.close()
      # --- precinct level via the institution list (US House district -> precincts)
      pg=await newpage(W,H); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
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
