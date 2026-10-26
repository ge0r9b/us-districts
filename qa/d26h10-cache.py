# Oct 26 ~10 AM (1623): QA-138 fix regression check. Town rows (precRowsIn via __pri) per year computed with the new 1623 per-year caches, interleaved years,
# vs a fresh computation with all caches (__pr, __mv) cleared. Also town sum vs county precinct sum and unassigned count. Chromium 390x844.
import asyncio,json,sys,time
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
JS="""([st,cn])=>{ const T=window.__townsIn(st,cn); const src={'2016':(window.PREC16||{})[st],'2020':(window.PREC20||{})[st],'2024':PREC[st]};
 const S=(g)=>[g.length,g.reduce((x,r)=>x+(+r[2]||0),0),g.reduce((x,r)=>x+(+r[3]||0),0),g.reduce((x,r)=>x+(+r[4]||0),0)];
 const nm=d=>String(d[2]||d[1]);
 const run=(order)=>{const o={}; for(const y of order){ if(!src[y]) {o[y]='nosrc';continue;} o[y]=o[y]||{}; for(const d of T){ o[y][nm(d)]=S(window.__pri(d,src[y],cn)); } } return o;};
 const A=run(['2024','2016','2020','2024','2016','2020']);
 T.forEach(d=>{delete d.__pr; delete d.__mv;});
 const B={}; for(const y of ['2016','2020','2024']){ T.forEach(d=>{delete d.__pr; delete d.__mv;}); Object.assign(B,run([y])); }
 let diff=[]; for(const y of ['2016','2020','2024']){ if(A[y]==='nosrc'||B[y]==='nosrc'){diff.push([y,'nosrc',!!src[y]]);continue;} for(const k in A[y]) if(JSON.stringify(A[y][k])!==JSON.stringify(B[y][k])) diff.push([y,k,A[y][k],B[y][k]]); }
 const tot={}; for(const y of ['2016','2020','2024']){ if(!src[y]) continue; const rows=src[y].filter(r=>r[0]===cn); const used=new Set(); T.forEach(d=>window.__pri(d,src[y],cn).forEach(r=>used.add(r))); const s=S(rows), u=S([...used]); tot[y]={county:s,assigned:u,unassigned:s[0]-u[0]}; }
 const top={}; for(const y of ['2016','2020','2024']) if(A[y]!=='nosrc') top[y]=Object.entries(A[y]).sort((a,b)=>b[1][3]-a[1][3]).slice(0,4);
 return {towns:T.length,diff:diff.slice(0,10),ndiff:diff.length,tot,top}; }"""
async def main():
  eng=sys.argv[1] if len(sys.argv)>1 else 'chromium'
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); out={}
    for st,ab,cn in [('Massachusetts','MA','Worcester'),('Washington','WA','King'),('Illinois','IL','Cook'),('Texas','TX','Harris'),('Kentucky','KY','Jefferson'),('Colorado','CO','Denver'),('Michigan','MI','Wayne')]:
      c,pg,log=await ctx(b,390,844,True,eng)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
      for lvl in [ab,cn]:
        xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
      t0=time.time()
      for y in (0,1,2): await pg.evaluate(f"()=>window.__ySetYr({y})"); await pg.wait_for_timeout(4000)
      tl=round(time.time()-t0,1)
      try: r=await asyncio.wait_for(pg.evaluate(JS,[st,cn+' County']),120)
      except Exception as e: r={'EXC':str(e)[:300]}
      r['yr_cycle_s']=tl; r['pageerr']=log['pageerr']; out[cn]=r; print(st,cn,json.dumps(r)[:1500],flush=True); await c.close()
    json.dump(out,open(f'b1623d26h10-cache-{eng}.json','w'),indent=1); await b.close()
asyncio.run(main())
