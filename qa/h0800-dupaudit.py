# Oct 25 8AM (1618): QA-119 family hunt at data level. For each county, assign precincts to towns with the app's own precRowsIn()
# and list precincts that land in 2+ towns, and towns whose precinct names name another town of the county.
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
JS="""async (st)=>{ await window.__townAudit(st); const rows=PREC[st]||[];
 const inRing=(x,y,R)=>{let c=false;for(let i=0,j=R.length-1;i<R.length;j=i++){const [xi,yi]=R[i],[xj,yj]=R[j];if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))c=!c;}return c;};
 const inPolys=(P,x,y)=>{ if(!P) return false; for(const rings of P){ if(!rings||!rings[0]) continue; if(inRing(x,y,rings[0])){ let h=false; for(let k=1;k<rings.length;k++) if(inRing(x,y,rings[k])) h=true; if(!h) return true; } } return false; };
 const cen=r=>{ if(r.__qc) return r.__qc; let A=0,cx=0,cy=0; for(const rings of r[5]){ const R=rings[0]; for(let i=0,j=R.length-1;i<R.length;j=i++){const f=R[j][0]*R[i][1]-R[i][0]*R[j][1];A+=f;cx+=(R[j][0]+R[i][0])*f;cy+=(R[j][1]+R[i][1])*f;} } let c=A?[cx/(3*A),cy/(3*A)]:[(r[6][0]+r[6][2])/2,(r[6][1]+r[6][3])/2]; if(!inPolys(r[5],c[0],c[1])) c=[(r[6][0]+r[6][2])/2,(r[6][1]+r[6][3])/2]; return r.__qc=c; };
 const precRowsIn=(d,rows,cn)=>rows.filter(r=>{ if(r[0]!==cn) return false; const [x,y]=cen(r); return inPolys(d[3],x,y); });
 const townsIn=window.__townsIn; const out={st,nprec:rows.length,dups:[],named:[],ntowns:0};
 const cs=[...new Set(rows.map(r=>r[0]))];
 for(const cn of cs){ let T=[]; try{T=townsIn(st,cn);}catch(e){continue;} out.ntowns+=T.length; const own=new Map();
  const base=n=>n.replace(/ (city|town|village|borough|CDP|township|municipality|plantation|charter township)$/i,'').trim();
  for(const d of T){ const pr=precRowsIn(d,rows,cn); for(const r of pr){ if(!own.has(r)) own.set(r,[]); own.get(r).push(d[2]); }
    const b=base(d[2]);
    for(const r of pr){ const nm=String(r[1]); for(const o of T){ if(o===d) continue; const ob=base(o[2]); if(ob.length>3&&ob!==b&&nm.toLowerCase().includes(ob.toLowerCase())&&!(b.toLowerCase().includes(ob.toLowerCase()))&&!nm.toLowerCase().startsWith(b.toLowerCase())) out.named.push({c:cn,town:d[2],prec:nm,names:o[2],tot:r[4]}); } } }
  for(const [r,ts] of own) if(ts.length>1) out.dups.push({c:cn,prec:String(r[1]),towns:ts,tot:r[4]}); }
 return out; }"""
async def main():
  sts=sys.argv[1].split(','); res=[]
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(3000)
    for st in sts:
      try: r=await pg.evaluate(JS,st)
      except Exception as e: r={'st':st,'err':str(e)[:200]}
      print(st,r.get('nprec'),r.get('ntowns'),'dups',len(r.get('dups',[])),'named',len(r.get('named',[])),flush=True); res.append(r)
    json.dump(res,open('b1618h0800-dupaudit-%s.json'%sys.argv[2],'w'),indent=0)
    await b.close()
asyncio.run(main())
