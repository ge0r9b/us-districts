# Oct 25 (1620): audit of the place-membership gate with the app's own precRowsIn (window.__pri) vs centroid-only membership
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
JS="""async (st)=>{ await window.__townAudit(st); const rows=PREC[st]||[];
 const inRing=(x,y,R)=>{let c=false;for(let i=0,j=R.length-1;i<R.length;j=i++){const [xi,yi]=R[i],[xj,yj]=R[j];if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))c=!c;}return c;};
 const inPolys=(P,x,y)=>{ if(!P) return false; for(const rings of P){ if(!rings||!rings[0]) continue; if(inRing(x,y,rings[0])){ let h=false; for(let k=1;k<rings.length;k++) if(inRing(x,y,rings[k])) h=true; if(!h) return true; } } return false; };
 const cen=r=>{ if(r.__qc) return r.__qc; let A=0,cx=0,cy=0; for(const rings of r[5]){ const R=rings[0]; for(let i=0,j=R.length-1;i<R.length;j=i++){const f=R[j][0]*R[i][1]-R[i][0]*R[j][1];A+=f;cx+=(R[j][0]+R[i][0])*f;cy+=(R[j][1]+R[i][1])*f;} } let c=A?[cx/(3*A),cy/(3*A)]:[(r[6][0]+r[6][2])/2,(r[6][1]+r[6][3])/2]; if(!inPolys(r[5],c[0],c[1])) c=[(r[6][0]+r[6][2])/2,(r[6][1]+r[6][3])/2]; return r.__qc=c; };
 const out={st,nprec:rows.length,moved:[],dups:[],sharedBase:[],ntowns:0};
 const cs=[...new Set(rows.map(r=>r[0]))];
 for(const cn of cs){ let T=[]; try{T=window.__townsIn(st,cn);}catch(e){continue;} if(!T.length) continue; out.ntowns+=T.length;
  const gate=new Map(), geo=new Map();
  for(const d of T){ for(const r of window.__pri(d,rows,cn)){ if(!gate.has(r)) gate.set(r,[]); gate.get(r).push(d[2]); }
    for(const r of rows){ if(r[0]!==cn) continue; const [x,y]=cen(r); if(inPolys(d[3],x,y)){ if(!geo.has(r)) geo.set(r,[]); geo.get(r).push(d[2]); } } }
  for(const [r,ts] of gate) if(ts.length>1) out.dups.push({c:cn,prec:String(r[1]),towns:ts,tot:r[4]});
  for(const r of rows){ if(r[0]!==cn) continue; const a=(gate.get(r)||[]).join('+'), b=(geo.get(r)||[]).join('+'); if(a!==b) out.moved.push({c:cn,prec:String(r[1]),to:a,from:b,tot:r[4]}); }
  const bs={}; for(const d of T){ const b=(window.twBase?twBase(d[2]):d[2]); (bs[b]=bs[b]||[]).push(d[2]); } for(const b in bs) if(bs[b].length>1) out.sharedBase.push({c:cn,base:b,towns:bs[b]}); }
 return out; }"""
async def main():
  sts=sys.argv[1].split(','); res=[]
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(3000)
    for st in sts:
      try: r=await pg.evaluate(JS,st)
      except Exception as e: r={'st':st,'err':str(e)[:200]}
      print(st,r.get('nprec'),r.get('ntowns'),'moved',len(r.get('moved',[])),'dups',len(r.get('dups',[])),'shared',len(r.get('sharedBase',[])),r.get('err',''),flush=True); res.append(r)
    json.dump(res,open('b1620-gate-%s.json'%sys.argv[2],'w'),indent=0)
    await b.close()
asyncio.run(main())
