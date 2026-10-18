# pass 11 (build 1576): district-type lists outside PA. Row counts vs official chamber sizes, missing/odd values, duplicate names, tap latency.
import asyncio,sys,json,re
from playwright.async_api import async_playwright
from common import *
from gaps import fresh,ST
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>({n:(r.querySelector('.nmx')||r).textContent.trim(),t:r.innerText.replace(/\\n/g,' | '),vis:!!r.offsetParent}))"
PICK="n=>{const rs=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent);const r=rs.find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()===n});if(!r)return null;r.scrollIntoView({block:'center'});const q=(r.querySelector('.nmx')||r).getBoundingClientRect();return [q.left+q.width/2,q.top+q.height/2]}"
OFF={'senate':{'Texas':31,'California':40,'New York':63,'Ohio':33,'Florida':40,'Nebraska':49,'Minnesota':67,'New Hampshire':24},
     'house':{'Texas':150,'California':80,'New York':150,'Ohio':99,'Florida':120,'Minnesota':134,'New Hampshire':None},
     'school':{'Texas':None,'Ohio':None,'Hawaii':1,'Florida':67,'Nebraska':None}}
AB={'Texas':'TX','California':'CA','New York':'NY','Ohio':'OH','Florida':'FL','Nebraska':'NE','Minnesota':'MN','New Hampshire':'NH','Hawaii':'HI'}
LAB={'senate':'State senate districts','house':'State house districts','school':'School districts'}
async def main():
  eng=sys.argv[1] if len(sys.argv)>1 else 'chromium'; W,H=(int(sys.argv[2]),int(sys.argv[3])) if len(sys.argv)>3 else (390,844); tag=f"{W}x{H}" if W>600 else str(W)
  out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for k,states in OFF.items():
      for stn,exp in states.items():
        print('start',k,stn,flush=True); c,pg,log=await fresh(b,eng,W,H); R={'exp':exp}; print(' loaded',flush=True)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        xy=await pg.evaluate("l=>{const e=[...document.querySelectorAll('li')].find(e=>e.offsetParent&&e.innerText.replace(/^[SH]\\n?/,'').trim()===l);if(!e)return null;const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",LAB[k])
        if not xy: R['err']='menu item missing'; out[k+':'+stn]=R; await c.close(); continue
        R['lat_open']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
        print(' opened',R['lat_open'],flush=True); l1=await pg.evaluate(ROWS); R['l1_n']=len(l1); R['l1_lv']=await pg.evaluate("()=>window.__laInfo().lv")
        xy=await pg.evaluate(PICK,AB[stn])
        if not xy: R['err']='state row missing'; R['l1_head']=[r['t'] for r in l1[:5]]; out[k+':'+stn]=R; await c.close(); continue
        await pg.wait_for_timeout(300); R['lat_state']=await tap_latency(pg,*xy); await pg.wait_for_timeout(6000)
        print(' state tapped',flush=True); rows=await pg.evaluate(ROWS); R['lv']=await pg.evaluate("()=>window.__laInfo().lv"); R['st']=await pg.evaluate(ST)
        R['n']=len(rows); names=[r['n'] for r in rows]
        R['dups']=sorted({n for n in names if names.count(n)>1})[:10]
        R['odd']=[r['t'] for r in rows if re.search(r'n/a|NaN|undefined|null|Infinity|—\s*$',r['t']) or not re.search(r'\d',r['t'].split('|',1)[-1])][:8]
        R['head']=[r['t'] for r in rows[:4]]; R['tail']=[r['t'] for r in rows[-2:]]
        # % sums: rows with two percentages
        R['err']=log['pageerr']+[x for x in log['console'] if 'error' in x][:5]+log['http'][:5]
        await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{tag}-{k}-{stn.replace(' ','')}.png")
        # drill one district
        if rows:
          xy=await pg.evaluate(PICK,rows[0]['n'])
          if xy:
            await pg.wait_for_timeout(300); R['lat_drill']=await tap_latency(pg,*xy); await pg.wait_for_timeout(5000)
            R['drill']={'st':await pg.evaluate(ST),'rows':[r['t'] for r in (await pg.evaluate(ROWS))[:3]]}
            await safeshot(pg,f"../shots/b1576p11-{eng[:2]}-{tag}-{k}-{stn.replace(' ','')}-drill.png")
        out[k+':'+stn]=R; print(k,stn,R.get('n'),'exp',exp,R.get('dups'),R.get('odd')[:2],R.get('lat_open'),R.get('lat_state'),R.get('lat_drill'),flush=True)
        await c.close()
  json.dump(out,open(f'b1576p11-dist-{eng}-{tag}.json','w'),indent=1)
if __name__=='__main__': asyncio.run(main())
