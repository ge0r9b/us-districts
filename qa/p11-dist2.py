# pass 11: state > district type (layers menu) > list. Row counts vs official chamber sizes, odd values, dups, latency.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>({n:(r.querySelector('.nmx')||r).textContent.trim(),t:r.innerText.replace(/\\n/g,' | ')}))"
CASES=[('Texas','senate',31),('Texas','statehouse',150),('California','senate',40),('California','statehouse',80),('New York','senate',63),('New York','statehouse',150),('Ohio','senate',33),('Ohio','statehouse',99),('Nebraska','senate',49),('Minnesota','statehouse',134),('Florida','school',67),('Hawaii','school',1),('Ohio','school',None)]
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    xy=await center(pg,'#bLyr'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
    keys=await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow .lbtn')].map(b=>[b.dataset.k,b.getAttribute('aria-label')||b.textContent.trim()])"); print('keys',keys,flush=True); out['keys']=keys; await c.close()
    for stn,k,exp in CASES:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R={'exp':exp}
      await typegq(pg,stn); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
      xy=await center(pg,'#bLyr'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
      xy=await center(pg,f'#lyrRow .lbtn[data-k={k}]')
      if not xy: R['err']='no layer btn'; out[stn+':'+k]=R; print(stn,k,R,flush=True); await c.close(); continue
      R['lat_type']=await tap_latency(pg,*xy); await pg.wait_for_timeout(4000)
      xy=await center(pg,'#bGlobe'); R['lat_list']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000)
      rows=await pg.evaluate(ROWS); R['st']=await pg.evaluate(ST); R['n']=len(rows); names=[r['n'] for r in rows]
      R['dups']=sorted({n for n in names if names.count(n)>1})[:10]
      R['odd']=[r['t'] for r in rows if re.search(r'n/a|NaN|undefined|null|Infinity',r['t']) or not re.search(r'\d',r['t'].split('|',1)[-1] if '|' in r['t'] else '')][:8]
      R['head']=[r['t'] for r in rows[:3]]; R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:5]+log['http'][:5]
      await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{W}-{k}-{stn.replace(' ','')}-list.png")
      out[stn+':'+k]=R; print(stn,k,'n',R['n'],'exp',exp,'dups',R['dups'][:3],'odd',len(R['odd']),R['odd'][:2],'lat',R['lat_type'],R['lat_list'],R['head'][:2],R['st']['crumb'],R['err'][:2],flush=True)
      await c.close()
  json.dump(out,open(f'b1576p11-dist2-{eng}-{W}.json','w'),indent=1)
asyncio.run(main())
